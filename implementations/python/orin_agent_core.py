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


@dataclass(frozen=True)
class DecisionPrompt:
    uncertainty_id: str
    question: str
    why_it_matters: str
    affected_objects: tuple[str, ...]
    options: tuple[DecisionOption, ...]

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

DECISION_PROMPTS = {
    RATE_LIMIT_UNCERTAINTY_ID: RATE_LIMIT_PROMPT,
}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _password_reset_source_path() -> Path:
    return _repository_root() / "examples" / "password-reset.orin"


def _password_reset_structured_path() -> Path:
    return _repository_root() / "tests" / "conformance" / "password-reset.structured.json"


class OrinDecisionAgent:
    """Focused offline agent for unresolved consequential decisions."""

    def inspect(self, path: str | Path) -> InspectionResult:
        artifact = self._load_artifact(path)
        report = artifact.model.readiness_report()
        decisions: list[DecisionNeed] = []
        for diagnostic in report.diagnostics:
            if (
                diagnostic.category == "unresolved-assumption"
                and diagnostic.blocking
                and diagnostic.object_id in DECISION_PROMPTS
            ):
                decisions.append(
                    DecisionNeed(
                        prompt=DECISION_PROMPTS[diagnostic.object_id],
                        diagnostic=diagnostic,
                    )
                )
        return InspectionResult(
            source_path=artifact.source_path,
            source_kind=artifact.source_kind,
            semantic_path=artifact.semantic_path,
            compilation=artifact.model.compilation_status(),
            validation_status=report.validation_status,
            decisions=tuple(decisions),
            diagnostics=report.diagnostics,
        )

    def apply_decision(
        self,
        path: str | Path,
        uncertainty_id: str,
        option_id: str | None,
    ) -> DecisionApplicationResult:
        inspection = self.inspect(path)
        if not inspection.decisions:
            raise DecisionRequiredError(
                "no blocking consequential decision is available for this artifact"
            )
        available_uncertainty_ids = {
            decision.prompt.uncertainty_id
            for decision in inspection.decisions
        }
        if uncertainty_id not in available_uncertainty_ids:
            raise UnknownDecisionError(
                f"artifact does not expose blocking uncertainty '{uncertainty_id}'"
            )
        prompt = DECISION_PROMPTS.get(uncertainty_id)
        if prompt is None:
            raise UnknownDecisionError(f"unknown uncertainty '{uncertainty_id}'")
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

        artifact = self._load_artifact(path)
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
            "id": RATE_LIMIT_RULE_ID,
            "kind": "rule",
            "name": "reset-request-rate-limit",
            "status": "accepted",
            "claims": list(option.rule_claims),
        }
        replaced = False
        for index, obj in enumerate(objects):
            if isinstance(obj, dict) and obj.get("id") == RATE_LIMIT_RULE_ID:
                objects[index] = updated_rule
                replaced = True
                break
        if not replaced:
            objects.append(updated_rule)

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
            return LoadedArtifact(
                source_path=source_path,
                source_kind="semantic-document",
                semantic_path=source_path,
                model=model,
            )
        if suffix == ".orin":
            if source_path == _password_reset_source_path().resolve():
                return self._load_password_reset_source(source_path)
            try:
                model = OrinParser().parse_file(source_path)
                return LoadedArtifact(
                    source_path=source_path,
                    source_kind="orin-source",
                    semantic_path=None,
                    model=model,
                )
            except ValueError as error:
                if source_path == PASSWORD_RESET_SOURCE.resolve():
                    return self._load_password_reset_source(source_path)
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
            "module: password-reset",
            "uncertainty: rate-limit",
            "Should reset requests be rate-limited?",
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
            "   Affected objects:",
        ])
        for object_id in prompt.affected_objects:
            lines.append(f"   - {object_id}")
        lines.append("   Options:")
        for option in prompt.options:
            lines.append(f"   - {option.id}: {option.label}")
            lines.append(f"     Why choose it: {option.explanation}")
            lines.append(f"     Compilation: {option.compilation}")
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

    decide_parser = subparsers.add_parser(
        "decide",
        help="Apply an explicit human decision and emit a revised semantic artifact.",
    )
    decide_parser.add_argument("path")
    decide_parser.add_argument("--uncertainty", required=True)
    decide_parser.add_argument("--option")
    decide_parser.add_argument("--write")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    agent = OrinDecisionAgent()
    try:
        if args.command == "inspect":
            inspection = agent.inspect(args.path)
            print(_format_inspection(inspection))
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
