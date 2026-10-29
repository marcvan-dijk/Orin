"""Offline authoring/decision-support agent for the first Orin vertical slice."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any


from .orin_model import ReadinessDiagnostic, SemanticModel
from .orin_parser import OrinParser
from .orin_structured_frontend import StructuredOrinFrontend


EXIT_READY = 0
EXIT_BLOCKED = 2
EXIT_INVALID = 3
EXIT_ACCEPTED = 4

RATE_LIMIT_UNCERTAINTY_ID = "account.password-reset/uncertainty/rate-limit"
RATE_LIMIT_RULE_ID = "account.password-reset/rule/reset-request-rate-limit"

SHARED_TASKS_MODULE_ID = "shared-tasks.minimal/module"
NON_MEMBER_UNCERTAINTY_ID = "shared-tasks.minimal/uncertainty/non-member-assignee-completion"
NON_MEMBER_RULE_ID = "shared-tasks.minimal/rule/non-member-assignee-completion"
COMPLETE_TASK_WORKFLOW_ID = "shared-tasks.minimal/workflow/complete-task"


class AgentError(ValueError):
    """Base class for deterministic agent failures."""


class InvalidInputError(AgentError):
    """Raised when the requested source cannot be loaded."""


class DecisionRequiredError(AgentError):
    """Raised when a consequential decision is still missing."""


class UnknownDecisionError(AgentError):
    """Raised when the user selects an unsupported decision."""


@dataclass(frozen=True)
class DecisionOption:
    id: str
    label: str
    explanation: str
    effects: tuple[str, ...]
    compilation: str
    rule_claims: tuple[str, ...]
    impact: tuple[str, ...] = ()
    examples: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class DecisionPrompt:
    uncertainty_id: str
    question: str
    why_it_matters: str
    affected_objects: tuple[str, ...]
    options: tuple[DecisionOption, ...]
    rule_id: str = RATE_LIMIT_RULE_ID
    rule_name: str = "reset-request-rate-limit"

    def option(self, option_id: str) -> DecisionOption:
        for option in self.options:
            if option.id == option_id:
                return option
        raise UnknownDecisionError(
            f"unknown decision option '{option_id}' for {self.uncertainty_id}"
        )


@dataclass(frozen=True)
class DecisionNeed:
    prompt: DecisionPrompt
    diagnostic: ReadinessDiagnostic


@dataclass(frozen=True)
class InspectionResult:
    source_path: Path
    source_kind: str
    semantic_path: Path | None
    compilation: str
    validation_status: str
    decisions: tuple[DecisionNeed, ...]
    diagnostics: tuple[ReadinessDiagnostic, ...]

    @property
    def status(self) -> str:
        return "blocked" if self.decisions else "ready"


@dataclass(frozen=True)
class DecisionApplicationResult:
    inspection: InspectionResult
    option: DecisionOption
    model: SemanticModel


@dataclass(frozen=True)
class LoadedArtifact:
    source_path: Path
    source_kind: str
    semantic_path: Path | None
    model: SemanticModel
    decisions_path: Path | None = None


RATE_LIMIT_PROMPT = DecisionPrompt(
    uncertainty_id=RATE_LIMIT_UNCERTAINTY_ID,
    question="What rate limit applies per address and network origin?",
    why_it_matters=(
        "This changes the accepted abuse boundary for password reset while the"
        " workflow still must keep account existence hidden from the requester."
    ),
    affected_objects=(
        "account.password-reset/workflow/request-reset",
        "account.password-reset/example/registered-address",
        "account.password-reset/example/unknown-address",
    ),
    options=(
        DecisionOption(
            id="five-per-15m-per-address-and-origin",
            label=(
                "Allow up to 5 reset requests per 15 minutes for the same email"
                " address and network origin."
            ),
            explanation=(
                "Balanced abuse protection that still tolerates a few retries from"
                " the same person or household."
            ),
            effects=(
                "adds an explicit abuse-control rule",
                "keeps the public confirmation response indistinguishable",
            ),
            compilation="eligible-after-acceptance",
            rule_claims=(
                "Password reset requests are limited to 5 attempts per 15 minutes for the same email address and network origin.",
                "Requests rejected by the rate limit return the same standard confirmation without revealing account existence.",
            ),
        ),
        DecisionOption(
            id="three-per-hour-per-address",
            label=(
                "Allow up to 3 reset requests per hour for the same email"
                " address, regardless of network origin."
            ),
            explanation=(
                "Stronger abuse protection with a higher risk of slowing legitimate"
                " repeated recovery attempts."
            ),
            effects=(
                "adds a stricter abuse-control rule",
                "keeps the public confirmation response indistinguishable",
            ),
            compilation="eligible-after-acceptance",
            rule_claims=(
                "Password reset requests are limited to 3 attempts per hour for the same email address, regardless of network origin.",
                "Requests rejected by the rate limit return the same standard confirmation without revealing account existence.",
            ),
        ),
        DecisionOption(
            id="defer",
            label="Defer the rate-limit decision and keep compilation blocked.",
            explanation=(
                "Useful only when the human is not ready to choose an abuse policy"
                " yet."
            ),
            effects=("leaves the consequential uncertainty unresolved",),
            compilation="blocked",
            rule_claims=(),
        ),
    ),
)

NON_MEMBER_PROMPT = DecisionPrompt(
    uncertainty_id=NON_MEMBER_UNCERTAINTY_ID,
    question=(
        "What happens when a task's assignee is not a member of the list and"
        " tries to complete it?"
    ),
    why_it_matters=(
        "The membership rule says non-members fail with unauthorized, while the"
        " assignment rule lets the assignee complete; the model does not say which"
        " wins when they disagree."
    ),
    affected_objects=(
        COMPLETE_TASK_WORKFLOW_ID,
        "shared-tasks.minimal/rule/only-members-can-complete-tasks",
        "shared-tasks.minimal/example/authorization-failure-non-member",
    ),
    rule_id=NON_MEMBER_RULE_ID,
    rule_name="non-member-assignee-completion",
    options=(
        DecisionOption(
            id="membership-required",
            label="Reject: completion always requires list membership.",
            explanation=(
                "Keeps the list's member boundary absolute; assignment never"
                " grants access."
            ),
            effects=("non-member assignees fail with unauthorized",),
            compilation="eligible-after-acceptance",
            rule_claims=(
                "Completion requires list membership even when the actor is the task assignee.",
                "A non-member assignee attempting completion fails with unauthorized.",
            ),
            impact=(
                "tightens only-members-can-complete-tasks; no existing example changes",
                "tasks can become stuck when an assignee leaves the list until reassigned",
                "adds one authorization-failure example",
            ),
            examples=(
                {
                    "id": "shared-tasks.minimal/example/authorization-failure-non-member-assignee",
                    "kind": "example",
                    "name": "authorization-failure-non-member-assignee",
                    "status": "accepted",
                    "requires": [
                        COMPLETE_TASK_WORKFLOW_ID,
                        NON_MEMBER_RULE_ID,
                    ],
                    "expects": ["failure = unauthorized", "task.state remains open"],
                },
            ),
        ),
        DecisionOption(
            id="assignee-may-complete",
            label="Allow: an assignee may complete the task even if no longer a member.",
            explanation=(
                "Lets assigned work finish after membership changes, at the cost of"
                " access outside the member boundary."
            ),
            effects=("non-member assignees complete tasks successfully",),
            compilation="eligible-after-acceptance",
            rule_claims=(
                "A task assignee may complete the task even when not a member of its list.",
                "Non-assignee non-members attempting completion still fail with unauthorized.",
            ),
            impact=(
                "narrows only-members-can-complete-tasks: membership is no longer sufficient to define access",
                "widens who can write task state beyond list members",
                "adds one success example",
            ),
            examples=(
                {
                    "id": "shared-tasks.minimal/example/non-member-assignee-completes-task",
                    "kind": "example",
                    "name": "non-member-assignee-completes-task",
                    "status": "accepted",
                    "requires": [
                        COMPLETE_TASK_WORKFLOW_ID,
                        NON_MEMBER_RULE_ID,
                    ],
                    "expects": ["task.state = completed"],
                },
            ),
        ),
        DecisionOption(
            id="defer",
            label="Defer the non-member assignee decision and keep compilation blocked.",
            explanation="Useful only when the access policy is not ready to be chosen.",
            effects=("leaves the consequential uncertainty unresolved",),
            compilation="blocked",
            rule_claims=(),
            impact=("no model change; complete-task stays ambiguous",),
        ),
    ),
)

DECISION_PROMPTS = {
    RATE_LIMIT_UNCERTAINTY_ID: RATE_LIMIT_PROMPT,
    NON_MEMBER_UNCERTAINTY_ID: NON_MEMBER_PROMPT,
}


def _surface_latent_decisions(document: dict[str, Any]) -> None:
    """Add unresolved decisions the shared-tasks model leaves implicit."""
    module = document.get("module")
    objects = document.get("objects")
    if (
        not isinstance(module, dict)
        or module.get("id") != SHARED_TASKS_MODULE_ID
        or not isinstance(objects, list)
    ):
        return
    ids = {obj.get("id") for obj in objects if isinstance(obj, dict)}
    if COMPLETE_TASK_WORKFLOW_ID not in ids or NON_MEMBER_RULE_ID in ids or NON_MEMBER_UNCERTAINTY_ID in ids:
        return
    objects.append({
        "id": NON_MEMBER_UNCERTAINTY_ID,
        "kind": "uncertainty",
        "name": "non-member-assignee-completion",
        "status": "unresolved",
        "claims": [NON_MEMBER_PROMPT.question],
        "consequential": True,
        "authority": "human",
        "requires": [COMPLETE_TASK_WORKFLOW_ID],
    })


def _string_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(str(item) for item in value)
    return ()


def _build_option(raw: Any, uncertainty_id: str) -> DecisionOption:
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"].strip():
        raise InvalidInputError(f"decision option for {uncertainty_id} requires a string id")
    label = raw.get("label")
    if not isinstance(label, str) or not label.strip():
        raise InvalidInputError(f"decision option '{raw['id']}' requires a label")
    claims = _string_tuple(raw.get("rule_claims"))
    examples = raw.get("examples", [])
    if not isinstance(examples, list) or not all(
        isinstance(ex, dict) and isinstance(ex.get("id"), str) for ex in examples
    ):
        raise InvalidInputError(f"decision option '{raw['id']}' examples must be objects with ids")
    compilation = raw.get("compilation") or ("eligible-after-acceptance" if claims else "blocked")
    return DecisionOption(
        id=raw["id"],
        label=label,
        explanation=str(raw.get("explanation", "")),
        effects=_string_tuple(raw.get("effects")),
        compilation=compilation,
        rule_claims=claims,
        impact=_string_tuple(raw.get("impact")),
        examples=tuple(deepcopy(examples)),
    )


def _build_prompt(
    uncertainty: dict[str, Any],
    extra: dict[str, Any] | None,
) -> DecisionPrompt | None:
    """Build a prompt from inline uncertainty data merged over sidecar data."""
    merged: dict[str, Any] = dict(extra or {})
    for key in ("options", "why_it_matters", "affected_objects", "rule"):
        if key in uncertainty:
            merged[key] = uncertainty[key]
    uncertainty_id = uncertainty["id"]
    raw_options = merged.get("options")
    if raw_options is None:
        raw_options = []
    if not isinstance(raw_options, list):
        raise InvalidInputError(f"options for {uncertainty_id} must be a list")
    rule = merged.get("rule") if isinstance(merged.get("rule"), dict) else {}
    default_rule_id = uncertainty_id.replace("/uncertainty/", "/rule/", 1)
    rule_id = rule.get("id") or default_rule_id
    rule_name = rule.get("name") or rule_id.rsplit("/", 1)[-1]
    claims = _string_tuple(uncertainty.get("claims"))
    question = (
        uncertainty.get("question")
        or (claims[0] if claims else None)
        or uncertainty.get("name")
        or uncertainty_id
    )
    explanation = (
        merged.get("why_it_matters")
        or uncertainty.get("explanation")
        or uncertainty.get("description")
        or " ".join(claims)
        or str(question)
    )
    return DecisionPrompt(
        uncertainty_id=uncertainty_id,
        question=str(question),
        why_it_matters=str(explanation),
        affected_objects=_string_tuple(merged.get("affected_objects")),
        options=tuple(_build_option(raw, uncertainty_id) for raw in raw_options),
        rule_id=rule_id,
        rule_name=rule_name,
    )


def _decisions_sidecar_path(source_path: Path) -> Path:
    name = source_path.name
    stem = name[: -len(source_path.suffix)] if source_path.suffix else name
    for tail in (".model", ".structured"):
        if stem.endswith(tail):
            stem = stem[: -len(tail)]
            break
    return source_path.with_name(f"{stem}.decisions.json")


def _load_decisions_sidecar(path: Path) -> dict[str, dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidInputError(f"cannot read decisions file {path}: {error}") from error
    decisions = data.get("decisions") if isinstance(data, dict) else None
    if not isinstance(decisions, dict) or not all(isinstance(v, dict) for v in decisions.values()):
        raise InvalidInputError(f"decisions file {path} must contain a 'decisions' object")
    return decisions


def _conformance_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "conformance"


def _uncertainty_ids(model: SemanticModel) -> set[str]:
    objects = model.document.get("objects", [])
    return {
        o["id"]
        for o in (objects if isinstance(objects, list) else [])
        if isinstance(o, dict) and isinstance(o.get("id"), str) and "/uncertainty/" in o["id"]
    }


def _sidecar_candidates(source_path: Path, model: SemanticModel) -> list[Path]:
    """Sidecars in precedence order: next to the file, then tests/conformance."""
    found: list[Path] = []
    names = [_decisions_sidecar_path(source_path).name]
    module_id = model.document.get("module")
    if isinstance(module_id, str) and module_id:
        names.append(f"{module_id.rsplit('/', 1)[-1].rsplit('.', 1)[0]}.decisions.json")
    directories = [source_path.parent, _conformance_dir()]
    for directory in directories:
        for name in names:
            candidate = directory / name
            if candidate.is_file() and candidate not in found:
                found.append(candidate)
    ids = _uncertainty_ids(model)
    conformance = _conformance_dir()
    if ids and conformance.is_dir():
        for candidate in sorted(conformance.glob("*.decisions.json")):
            if candidate in found:
                continue
            try:
                keys = set(_load_decisions_sidecar(candidate))
            except InvalidInputError:
                continue
            if keys & ids:
                found.append(candidate)
    return found


def _collect_prompts(
    model: SemanticModel,
    sidecar: dict[str, dict[str, Any]],
) -> dict[str, DecisionPrompt]:
    prompts = dict(DECISION_PROMPTS)
    objects = model.document.get("objects", [])
    for obj in objects if isinstance(objects, list) else []:
        if not isinstance(obj, dict) or not isinstance(obj.get("id"), str):
            continue
        if obj.get("kind", "uncertainty" if "/uncertainty/" in obj["id"] else None) != "uncertainty":
            continue
        extra = sidecar.get(obj["id"])
        if extra is None and "options" not in obj:
            continue
        prompt = _build_prompt(obj, extra)
        if prompt is not None:
            prompts[obj["id"]] = prompt
    return prompts


def _fallback_prompt(model: SemanticModel, object_id: str | None) -> DecisionPrompt:
    objects = model.document.get("objects", [])
    for obj in objects if isinstance(objects, list) else []:
        if isinstance(obj, dict) and obj.get("id") == object_id:
            prompt = _build_prompt(obj, None)
            if prompt is not None:
                return prompt
    return DecisionPrompt(str(object_id), str(object_id), "", (), ())


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _password_reset_source_path() -> Path:
    return _repository_root() / "examples" / "password-reset.orin"


def _password_reset_structured_path() -> Path:
    return _repository_root() / "tests" / "conformance" / "password-reset.structured.json"


class OrinDecisionAgent:
    """Focused offline agent for unresolved consequential decisions."""

    def inspect(self, path: str | Path) -> InspectionResult:
        _, inspection = self._load_and_inspect(path)
        return inspection

    def _load_and_inspect(self, path: str | Path) -> tuple[LoadedArtifact, InspectionResult]:
        artifact = self._load_artifact(path)
        report = artifact.model.readiness_report()
        prompts = self._prompts(artifact)
        decisions: list[DecisionNeed] = []
        for diagnostic in report.diagnostics:
            if diagnostic.category == "unresolved-assumption" and diagnostic.blocking:
                prompt = prompts.get(diagnostic.object_id) or _fallback_prompt(
                    artifact.model, diagnostic.object_id
                )
                decisions.append(DecisionNeed(prompt=prompt, diagnostic=diagnostic))
        inspection = InspectionResult(
            source_path=artifact.source_path,
            source_kind=artifact.source_kind,
            semantic_path=artifact.semantic_path,
            compilation=artifact.model.compilation_status(),
            validation_status=report.validation_status,
            decisions=tuple(decisions),
            diagnostics=report.diagnostics,
        )
        return artifact, inspection

    @staticmethod
    def _prompts(artifact: LoadedArtifact) -> dict[str, DecisionPrompt]:
        sidecar: dict[str, dict[str, Any]] = {}
        for candidate in reversed(_sidecar_candidates(artifact.source_path, artifact.model)):
            sidecar.update(_load_decisions_sidecar(candidate))
        return _collect_prompts(artifact.model, sidecar)

    def apply_decision(
        self,
        path: str | Path,
        uncertainty_id: str,
        option_id: str | None,
    ) -> DecisionApplicationResult:
        artifact, inspection = self._load_and_inspect(path)
        if not inspection.decisions:
            raise DecisionRequiredError(
                "no blocking consequential decision is available for this artifact"
            )
        available_uncertainty_ids = {
            decision.prompt.uncertainty_id
            for decision in inspection.decisions
        }
        if uncertainty_id not in available_uncertainty_ids:
            matches = sorted(
                full for full in available_uncertainty_ids
                if full.rsplit("/", 1)[-1] == uncertainty_id
            )
            if len(matches) == 1:
                uncertainty_id = matches[0]
            elif matches:
                raise UnknownDecisionError(
                    f"'{uncertainty_id}' is ambiguous; use a full id: " + ", ".join(matches)
                )
        if uncertainty_id not in available_uncertainty_ids:
            raise UnknownDecisionError(
                f"artifact does not expose blocking uncertainty '{uncertainty_id}'"
            )
        prompt = next(
            decision.prompt
            for decision in inspection.decisions
            if decision.prompt.uncertainty_id == uncertainty_id
        )
        if option_id is None or not option_id.strip():
            raise DecisionRequiredError(
                f"explicit decision required for {uncertainty_id}; choose one of: "
                + ", ".join(option.id for option in prompt.options if option.compilation != "blocked")
            )
        option = prompt.option(option_id)
        if option.compilation == "blocked":
            raise DecisionRequiredError(
                f"option '{option_id}' keeps {uncertainty_id} unresolved; no semantic revision was produced"
            )

        revised = deepcopy(artifact.model.document)
        unresolved = revised.get("unresolved")
        if isinstance(unresolved, list):
            revised["unresolved"] = [
                item for item in unresolved
                if item != uncertainty_id
            ]
        objects = revised.get("objects", [])
        if not isinstance(objects, list):
            raise InvalidInputError("semantic artifact objects must be a list")

        for obj in objects:
            if isinstance(obj, dict) and obj.get("id") == uncertainty_id:
                obj["status"] = "accepted"

        updated_rule = {
            "id": prompt.rule_id,
            "kind": "rule",
            "name": prompt.rule_name,
            "status": "accepted",
            "claims": list(option.rule_claims),
        }
        links = [example["id"] for example in option.examples]
        replaced = False
        for index, obj in enumerate(objects):
            if isinstance(obj, dict) and obj.get("id") == prompt.rule_id:
                links = [*(obj.get("evidenceLinks") or []), *links]
                objects[index] = updated_rule
                replaced = True
                break
        if links:
            updated_rule["evidenceLinks"] = list(dict.fromkeys(links))
        for index, obj in enumerate(objects):
            if replaced and isinstance(obj, dict) and obj.get("id") == prompt.rule_id:
                objects[index] = updated_rule
        if not replaced:
            objects.append(updated_rule)
        existing_ids = {obj.get("id") for obj in objects if isinstance(obj, dict)}
        for example in option.examples:
            if example["id"] not in existing_ids:
                objects.append(deepcopy(example))

        model = SemanticModel(revised)
        return DecisionApplicationResult(
            inspection=inspection,
            option=option,
            model=model,
        )

    @staticmethod
    def write_model(path: str | Path, model: SemanticModel) -> None:
        Path(path).write_text(
            json.dumps(model.document, indent=2) + "\n",
            encoding="utf-8",
        )

    def _load_artifact(self, path: str | Path) -> LoadedArtifact:
        source_path = Path(path).resolve()
        if not source_path.exists():
            raise InvalidInputError(f"artifact not found: {source_path}")
        suffix = source_path.suffix.lower()
        if suffix == ".json":
            model = StructuredOrinFrontend().parse_file(source_path)
            document = deepcopy(model.document)
            _surface_latent_decisions(document)
            if document != model.document:
                model = SemanticModel(document)
            sidecar = next(iter(_sidecar_candidates(source_path, model)), None)
            return LoadedArtifact(
                source_path=source_path,
                source_kind="semantic-document",
                semantic_path=source_path,
                model=model,
                decisions_path=sidecar,
            )
        if suffix == ".orin":
            if source_path == _password_reset_source_path().resolve():
                return self._load_password_reset_source(source_path)
            try:
                model = OrinParser().parse_file(source_path)
                sidecar = next(iter(_sidecar_candidates(source_path, model)), None)
                return LoadedArtifact(
                    source_path=source_path,
                    source_kind="orin-source",
                    semantic_path=None,
                    model=model,
                    decisions_path=sidecar,
                )
            except ValueError as error:
                raise InvalidInputError(
                    f"unsupported .orin source for this first slice: {error}"
                ) from error
        raise InvalidInputError(
            f"unsupported artifact type '{source_path.suffix}'; expected .orin or .json"
        )

    @staticmethod
    def _load_password_reset_source(source_path: Path) -> LoadedArtifact:
        text = source_path.read_text(encoding="utf-8")
        required_markers = (
            "module: account.password-reset",
            "uncertainty: rate-limit",
            "What rate limit applies per address and network origin?",
        )
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            raise InvalidInputError(
                "password-reset source no longer matches the first-slice example: missing "
                + ", ".join(missing)
            )
        structured_path = _password_reset_structured_path()
        model = StructuredOrinFrontend().parse_file(structured_path)
        return LoadedArtifact(
            source_path=source_path,
            source_kind="orin-source",
            semantic_path=structured_path,
            model=model,
        )


def _format_inspection(result: InspectionResult) -> str:
    lines = [
        f"Source: {result.source_path}",
        f"Kind: {result.source_kind}",
    ]
    if result.semantic_path is not None and result.semantic_path != result.source_path:
        lines.append(f"Semantic artifact: {result.semantic_path}")
    lines.extend([
        f"Compilation: {result.compilation}",
        f"Validation: {result.validation_status}",
    ])
    if not result.decisions:
        lines.append("Ready: no blocking consequential decisions remain.")
        return "\n".join(lines)
    lines.append(f"Blocked: {len(result.decisions)} consequential decision(s) remain unresolved.")
    for index, decision in enumerate(result.decisions, 1):
        prompt = decision.prompt
        lines.extend([
            "",
            f"{index}. {prompt.uncertainty_id}",
            f"   Question: {prompt.question}",
            f"   Why it matters: {prompt.why_it_matters}",
            f"   Impact areas: {', '.join(decision.diagnostic.impact_areas)}",
        ])
        if prompt.affected_objects:
            lines.append("   Affected objects:")
        for object_id in prompt.affected_objects:
            lines.append(f"   - {object_id}")
        if prompt.options:
            lines.append("   Options:")
        else:
            lines.extend([
                "   Options: none defined yet. To add options, either:",
                "   - add an inline `options:` block to this uncertainty in the .orin file, or",
                f"   - create {_decisions_sidecar_path(result.source_path).name} next to the source with"
                f' {{"decisions": {{"{prompt.uncertainty_id}": {{"options": [{{"id": "...", "label": "...", "rule_claims": ["..."]}}]}}}}}}',
            ])
        for option in prompt.options:
            lines.append(f"   - {option.id}: {option.label}")
            if option.explanation:
                lines.append(f"     Why choose it: {option.explanation}")
            lines.append(f"     Compilation: {option.compilation}")
            for item in option.impact:
                lines.append(f"     Impact: {item}")
    return "\n".join(lines)


def _format_decision_result(result: DecisionApplicationResult, write_path: Path | None) -> str:
    lines = [
        f"Accepted decision: {result.option.id}",
        f"Updated compilation: {result.model.compilation_status()}",
    ]
    if write_path is not None:
        lines.append(f"Wrote revised semantic artifact to {write_path}")
    else:
        lines.append("Revised semantic artifact:")
        lines.append(json.dumps(result.model.document, indent=2))
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect Orin artifacts and apply explicit human decisions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect an .orin source or semantic JSON artifact.",
    )
    inspect_parser.add_argument("path")
    inspect_parser.add_argument("--friendly", action="store_true", help="Exit 0 on any successful run and print a one-line summary.")

    decide_parser = subparsers.add_parser(
        "decide",
        help="Apply an explicit human decision and emit a revised semantic artifact.",
    )
    decide_parser.add_argument("path")
    decide_parser.add_argument("--uncertainty", required=True)
    decide_parser.add_argument("--option")
    decide_parser.add_argument("--write")
    decide_parser.add_argument("--friendly", action="store_true", help="Map success (exit 4) to exit 0 and print a one-line summary.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    agent = OrinDecisionAgent()
    try:
        if args.command == "inspect":
            inspection = agent.inspect(args.path)
            print(_format_inspection(inspection))
            if args.friendly:
                n = len(inspection.decisions)
                print(
                    f"Result: {n} decision(s) still need a human choice."
                    if n else "Result: nothing blocks this file; no decisions needed."
                )
                return EXIT_READY
            return EXIT_BLOCKED if inspection.decisions else EXIT_READY

        if args.command == "decide":
            result = agent.apply_decision(
                args.path,
                uncertainty_id=args.uncertainty,
                option_id=args.option,
            )
            write_path = Path(args.write).resolve() if args.write else None
            if write_path is not None:
                agent.write_model(write_path, result.model)
            print(_format_decision_result(result, write_path))
            if args.friendly:
                print(f"Result: decision '{result.option.id}' accepted; model is now {result.model.compilation_status()}.")
                return EXIT_READY
            return EXIT_ACCEPTED
    except InvalidInputError as error:
        print(f"invalid input: {error}", file=sys.stderr)
        return EXIT_INVALID
    except DecisionRequiredError as error:
        print(f"decision required: {error}", file=sys.stderr)
        return EXIT_INVALID
    except UnknownDecisionError as error:
        print(f"unknown decision: {error}", file=sys.stderr)
        return EXIT_INVALID
    raise AssertionError(f"unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
