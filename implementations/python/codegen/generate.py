"""Generate a standalone Python module from a ready Orin model.

Password-reset and expense-approval use hand-written templates; any other ready model with workflow transitions
is generated model-driven (see model_driven.py) together with a NotImplementedRule report.

Usage: python -m implementations.python.codegen.generate <model.json> <outdir>
"""

import argparse
import json
import re
import sys
from pathlib import Path

_PYTHON_DIR = Path(__file__).resolve().parents[1]
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

from orin_model import SemanticModel  # noqa: E402
from . import generic, model_driven, prose_driven  # noqa: E402

OUTPUT_NAME = "password_reset_generated.py"
WORKFLOW_ID = "account.password-reset/workflow/request-reset"
EXPIRY_RULE_ID = "account.password-reset/rule/reset-token-expiry"
SINGLE_USE_RULE_ID = "account.password-reset/rule/reset-token-single-use"
NO_DISCLOSURE_RULE_ID = "account.password-reset/rule/response-does-not-disclose-account"
RATE_LIMIT_RULE_ID = "account.password-reset/rule/reset-request-rate-limit"
EXPENSE_OUTPUT_NAME = "expense_approval_generated.py"
EXPENSE_MODULE_ID = "finance.expense-approval/module"
EXPENSE_RULES = (
    "finance.expense-approval/rule/approver-limit-covers-amount",
    "finance.expense-approval/rule/no-self-decision",
    "finance.expense-approval/rule/decision-is-final",
    "finance.expense-approval/rule/rejection-has-reason",
)
EXPENSE_WORKFLOW_ID = "finance.expense-approval/workflow/submit-expense"
_UNITS = {"second": 1, "minute": 60, "hour": 3600}


class GenerationError(Exception):
    """Raised when a model cannot be turned into an implementation."""


def sanitize_id(value: object) -> str:
    """Reduce a model-derived identifier to a charset that is inert in any emitted comment or literal."""
    return re.sub(r"[^A-Za-z0-9._/-]", "_", str(value))[:200]


def _render(template: str, values: dict[str, str]) -> str:
    """Single-pass placeholder substitution so substituted values are never rescanned."""
    return re.sub(r"@@([A-Z_]+)@@", lambda m: values[m.group(1)], template)


def _module_id(model: SemanticModel) -> object:
    module = model.document.get("module", {})
    if not isinstance(module, dict):
        raise GenerationError("malformed model: 'module' must be an object")
    return module.get("id")


def _object(model: SemanticModel, object_id: str) -> dict:
    if not isinstance(model.document.get("objects", []), list):
        raise GenerationError("malformed model: 'objects' must be a list")
    for obj in model.document.get("objects", []):
        if isinstance(obj, dict) and obj.get("id") == object_id:
            return obj
    raise GenerationError(f"model is missing required object: {object_id}")


def _claims(obj: dict) -> list[str]:
    claims = obj.get("claims", [])
    if not isinstance(claims, list):
        raise GenerationError(f"malformed model: claims of {sanitize_id(obj.get('id'))} must be a list")
    return [c for c in claims if isinstance(c, str)]


def _ttl_seconds(model: SemanticModel) -> int:
    for claim in _claims(_object(model, EXPIRY_RULE_ID)):
        match = re.search(r"expire after (\d+) (second|minute|hour)s?", claim)
        if match:
            return int(match.group(1)) * _UNITS[match.group(2)]
    raise GenerationError(f"cannot derive token lifetime from {EXPIRY_RULE_ID}")


def _rate_limit(model: SemanticModel) -> tuple[int, int, bool]:
    """Return (max attempts, window seconds, per network origin) from the accepted rule."""
    for claim in _claims(_object(model, RATE_LIMIT_RULE_ID)):
        match = re.search(
            r"limited to (\d+) attempts? per (?:(\d+) )?(second|minute|hour)s? for the same email address(.*)",
            claim,
        )
        if match:
            window = int(match.group(2) or 1) * _UNITS[match.group(3)]
            per_origin = "and network origin" in match.group(4)
            return int(match.group(1)), window, per_origin
    raise GenerationError(f"cannot derive rate limit from {RATE_LIMIT_RULE_ID}")


def _is_expense(model: SemanticModel) -> bool:
    return _module_id(model) == EXPENSE_MODULE_ID


def _has_object(model: SemanticModel, object_id: str) -> bool:
    objects = model.document.get("objects", [])
    return isinstance(objects, list) and any(isinstance(o, dict) and o.get("id") == object_id for o in objects)


def _is_model_driven(model: SemanticModel) -> bool:
    if _is_expense(model) or _has_object(model, WORKFLOW_ID) \
            or not model_driven.has_transition_workflows(model.document):
        return False
    try:
        model_driven.derive_ir(model.document)
    except model_driven.ModelDrivenError as error:
        # workflows without actor/subject inputs are outside model-driven scope: the generic generator takes them
        return "needs an actor input" not in str(error)
    return True


def _is_prose(model: SemanticModel) -> bool:
    return not _is_expense(model) and not _has_object(model, WORKFLOW_ID) \
        and not model_driven.has_transition_workflows(model.document) \
        and prose_driven.has_prose_rules(model.document)


def _is_generic(model: SemanticModel) -> bool:
    """Fallback: no dedicated generator matches, but the model has rules, workflows or examples."""
    return not _is_expense(model) and not _has_object(model, WORKFLOW_ID) \
        and _module_id(model) != "account.password-reset/module" \
        and not _is_model_driven(model) and not _is_prose(model)


def output_name(model: SemanticModel) -> str:
    if _is_expense(model):
        return EXPENSE_OUTPUT_NAME
    if _is_model_driven(model) or _is_prose(model) or _is_generic(model):
        return model_driven.output_stem(model.document.get("module", {})) + ".py"
    return OUTPUT_NAME


def _derive(model: SemanticModel) -> dict:
    try:
        return model_driven.derive_ir(model.document)
    except model_driven.ModelDrivenError as error:
        raise GenerationError(str(error)) from error


def _derive_prose(model: SemanticModel) -> dict:
    try:
        return prose_driven.derive_ir(model.document)
    except model_driven.ModelDrivenError as error:
        raise GenerationError(str(error)) from error


def _derive_generic(model: SemanticModel) -> dict:
    if not generic.has_content(model.document):
        raise GenerationError(
            f"no generator for module {sanitize_id(_module_id(model) or 'unknown')}: it has no rules, "
            "workflows or examples to generate from")
    try:
        return generic.derive_ir(model.document)
    except generic.GenericError as error:
        raise GenerationError(str(error)) from error


def generate_report(model: SemanticModel) -> dict | None:
    """Report of derived and NotImplementedRule rules for model-driven output; None for template output."""
    if _is_prose(model):
        return prose_driven.report(str(_module_id(model)), _derive_prose(model))
    if _is_generic(model):
        return generic.report(str(_module_id(model)), _derive_generic(model))
    if not _is_model_driven(model):
        return None
    return model_driven.report(str(_module_id(model)), _derive(model))


def generate_source(model: SemanticModel) -> str:
    _module_id(model)
    try:
        gates = model.compute_readiness_gates()
    except (AttributeError, TypeError, KeyError, ValueError) as error:
        raise GenerationError(f"malformed model: {error}") from error
    if gates["compilation"] != "eligible":
        blockers = ", ".join(gates.get("blockingUnresolved", [])) or "diagnostics present"
        raise GenerationError(
            f"model is not ready for generation (compilation={gates['compilation']}): {blockers}. "
            "Resolve the consequential decisions first."
        )
    module_id = sanitize_id(_module_id(model) or "unknown")
    if _is_expense(model):
        for object_id in (EXPENSE_WORKFLOW_ID, *EXPENSE_RULES):
            _object(model, object_id)
        return _render(_EXPENSE_TEMPLATE, {"MODULE": json.dumps(module_id)})
    if _is_model_driven(model):
        return _render(model_driven.TEMPLATE, {
            "MODULE": json.dumps(module_id),
            "IR": model_driven.render_ir(_derive(model)),
        })
    if _is_prose(model):
        return _render(prose_driven.TEMPLATE, {
            "MODULE": json.dumps(module_id),
            "IR": prose_driven.render_ir(_derive_prose(model)),
        })
    if _is_generic(model):
        return generic.render(module_id, _derive_generic(model))
    _object(model, WORKFLOW_ID)
    _object(model, SINGLE_USE_RULE_ID)
    _object(model, NO_DISCLOSURE_RULE_ID)
    limit, window, per_origin = _rate_limit(model)
    return _render(_TEMPLATE, {
        "MODULE": json.dumps(module_id),
        "TTL": str(_ttl_seconds(model)),
        "RATE_LIMIT": str(limit),
        "RATE_WINDOW": str(window),
        "RATE_PER_ORIGIN": str(per_origin),
    })


def _load_model(model_path: str | Path, outdir: Path, decisions: list[str]) -> SemanticModel:
    """Load a model.json, or an .orin source; each UNCERTAINTY=OPTION is applied through orin_agent_core."""
    path = Path(model_path)
    if path.suffix.lower() != ".orin" and not decisions:
        try:
            return SemanticModel.from_json_file(path)
        except json.JSONDecodeError as error:
            raise GenerationError(f"model is not valid JSON: {error}") from error
    from .. import orin_agent_core as core
    agent = core.OrinDecisionAgent()
    stages: list[Path] = []
    try:
        current: str | Path = path
        for index, spec in enumerate(decisions):
            uncertainty, sep, option = spec.partition("=")
            if not sep or not uncertainty or not option:
                raise GenerationError(f"--decide expects UNCERTAINTY=OPTION, got: {sanitize_id(spec)}")
            if "/" not in uncertainty:
                module = agent._load_artifact(path).model.document.get("module")
                module_id = module.get("id") if isinstance(module, dict) else module
                prefix = str(module_id).rsplit("/", 1)[0]
                uncertainty = f"{prefix}/uncertainty/{uncertainty}"
            result = agent.apply_decision(current, uncertainty, option)
            stage = outdir / f".orin-decision-stage-{index}.json"
            outdir.mkdir(parents=True, exist_ok=True)
            agent.write_model(stage, result.model)
            stages.append(stage)
            current = stage
        if path.suffix.lower() == ".orin" and not decisions:
            return agent._load_artifact(path).model
        return SemanticModel(json.loads(Path(current).read_text(encoding="utf-8")))
    except core.AgentError as error:
        raise GenerationError(f"decision failed: {error}") from error
    finally:
        for stage in stages:
            stage.unlink(missing_ok=True)


def generate(model_path: str | Path, outdir: str | Path, decisions: list[str] | None = None) -> Path:
    model = _load_model(model_path, Path(outdir), list(decisions or []))
    source = generate_source(model)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / output_name(model)
    target.write_text(source, encoding="utf-8", newline="\n")
    report = generate_report(model)
    if report is not None:
        target.with_suffix(".report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Python implementation from a ready Orin model.")
    parser.add_argument("model", help="path to a semantic model JSON file or an .orin source")
    parser.add_argument("outdir", help="directory to write the generated module into")
    parser.add_argument("--decide", action="append", default=[], metavar="UNCERTAINTY=OPTION",
                        help="apply a human decision first (repeatable; needs the decision sidecar)")
    args = parser.parse_args(argv)
    try:
        target = generate(args.model, args.outdir, args.decide)
    except (GenerationError, OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(target)
    return 0


_TEMPLATE = '''"""Generated by Orin codegen from model @@MODULE@@. Do not edit; regenerate instead."""

from dataclasses import dataclass, field

MODULE_ID = @@MODULE@@
PERSON_CAPABILITY = "person.request-password-reset"
SEND_MESSAGE_CAPABILITY = "system.send-reset-message"
TOKEN_TTL_SECONDS = @@TTL@@
STANDARD_RESPONSE = "standard-confirmation"
RATE_LIMIT_MAX_REQUESTS = @@RATE_LIMIT@@
RATE_LIMIT_WINDOW_SECONDS = @@RATE_WINDOW@@
RATE_LIMIT_PER_ORIGIN = @@RATE_PER_ORIGIN@@


class CapabilityDenied(Exception):
    """Raised when a workflow lacks a required capability."""


class TokenRejected(Exception):
    """Raised when a reset token is unknown, expired, or already used."""


@dataclass
class AccountStore:
    existing_addresses: set
    available: bool = True

    def lookup(self, email):
        if not self.available:
            raise RuntimeError("account store unavailable")
        return email in self.existing_addresses


@dataclass
class EmailProvider:
    available: bool = True
    sent_messages: list = field(default_factory=list)

    def send_reset_message(self, email):
        if not self.available:
            raise RuntimeError("email provider unavailable")
        self.sent_messages.append(email)


@dataclass
class ResetTokenStore:
    issued: dict = field(default_factory=dict)
    used: set = field(default_factory=set)
    next_id: int = 1

    def issue(self, email, now):
        token = f"reset-token-{self.next_id}"
        self.next_id += 1
        self.issued[token] = (email, now)
        return token

    def redeem(self, token, now):
        if token not in self.issued:
            raise TokenRejected("unknown token")
        if token in self.used:
            raise TokenRejected("token already used")
        email, issued_at = self.issued[token]
        if now - issued_at >= TOKEN_TTL_SECONDS:
            raise TokenRejected("token expired")
        self.used.add(token)
        return email


@dataclass(frozen=True)
class ResetResult:
    response: str
    reset_message: str
    account_existence_disclosed: bool
    recovery: str = None
    reset_token: str = None
    outputs: dict = field(default_factory=dict)
    failures: tuple = ()


class PasswordResetRuntime:
    """Execute request-reset; every outcome returns the same standard response."""

    def __init__(self, account_store, email_provider, token_store=None):
        self.account_store = account_store
        self.email_provider = email_provider
        self.token_store = token_store or ResetTokenStore()
        self._attempts = {}

    def _rate_limited(self, email, origin, now):
        key = (email, origin) if RATE_LIMIT_PER_ORIGIN else (email,)
        recent = [t for t in self._attempts.get(key, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(recent) >= RATE_LIMIT_MAX_REQUESTS:
            self._attempts[key] = recent
            return True
        recent.append(now)
        self._attempts[key] = recent
        return False

    def request_reset(self, email, capabilities, now=0, origin=""):
        if PERSON_CAPABILITY not in capabilities:
            raise CapabilityDenied(PERSON_CAPABILITY)
        if self._rate_limited(email, origin, now):
            return ResetResult(
                STANDARD_RESPONSE, "not-sent", False,
                outputs={"response": STANDARD_RESPONSE, "resetMessage": "not-sent", "accountExistenceDisclosed": False},
                failures=("rate-limit.exceeded",),
            )
        try:
            account_exists = self.account_store.lookup(email)
        except RuntimeError:
            return ResetResult(
                STANDARD_RESPONSE, "not-sent", False, "no-account-state-disclosed",
                outputs={"response": STANDARD_RESPONSE, "accountExistenceDisclosed": False},
                failures=("account-store.unavailable",),
            )
        if not account_exists:
            return ResetResult(
                STANDARD_RESPONSE, "not-sent", False,
                outputs={"response": STANDARD_RESPONSE, "resetMessage": "not-sent", "accountExistenceDisclosed": False},
            )
        if SEND_MESSAGE_CAPABILITY not in capabilities:
            raise CapabilityDenied(SEND_MESSAGE_CAPABILITY)
        token = self.token_store.issue(email, now)
        try:
            self.email_provider.send_reset_message(email)
        except RuntimeError:
            return ResetResult(
                STANDARD_RESPONSE, "not-sent", False, "no-account-state-disclosed", token,
                outputs={"response": STANDARD_RESPONSE, "resetMessage": "not-sent", "accountExistenceDisclosed": False},
                failures=("email-provider.unavailable",),
            )
        return ResetResult(
            STANDARD_RESPONSE, "sent", False, reset_token=token,
            outputs={"response": STANDARD_RESPONSE, "resetMessage": "sent", "accountExistenceDisclosed": False},
        )

    def redeem_reset(self, token, now):
        return self.token_store.redeem(token, now)

    def request_resets_concurrently(self, emails, capabilities, now=0, origin=""):
        """Deterministic input-order scheduling of concurrent requests."""
        return tuple(self.request_reset(email, capabilities, now, origin) for email in emails)
'''

_EXPENSE_TEMPLATE = '''"""Generated by Orin codegen from model @@MODULE@@. Do not edit; regenerate instead."""

from dataclasses import dataclass

MODULE_ID = @@MODULE@@
SUBMITTED = "submitted"
APPROVED = "approved"
REJECTED = "rejected"
TRANSITIONS = {SUBMITTED: (APPROVED, REJECTED), APPROVED: (), REJECTED: ()}


class Refused(Exception):
    """Raised when a rule refuses a decision; the expense state is unchanged."""


@dataclass
class Expense:
    id: str
    submitter: str
    amount: int
    state: str = SUBMITTED
    reason: str = None


@dataclass(frozen=True)
class Decision:
    expense: str
    reason: str = None
    reason_visible_to_submitter: bool = False


class ExpenseRuntime:
    """Execute submit-expense: submit, route to an eligible approver, record the decision."""

    def __init__(self):
        self.expenses = {}

    def submit(self, expense_id, submitter, amount):
        expense = Expense(expense_id, submitter, amount)
        self.expenses[expense_id] = expense
        return expense

    def eligible_approver(self, expense_id, approvers):
        """First approver (input order) who is not the submitter and whose limit covers the amount."""
        expense = self.expenses[expense_id]
        for name, limit in approvers:
            if name != expense.submitter and limit >= expense.amount:
                return name
        return None

    def _check(self, expense, approver, limit):
        if expense.state != SUBMITTED:
            raise Refused("decision-is-final")
        if approver == expense.submitter:
            raise Refused("no-self-decision")

    def approve(self, expense_id, approver, limit):
        expense = self.expenses[expense_id]
        self._check(expense, approver, limit)
        if limit < expense.amount:
            raise Refused("approver-limit-covers-amount")
        expense.state = APPROVED
        return Decision(expense.state)

    def reject(self, expense_id, approver, limit, reason):
        expense = self.expenses[expense_id]
        self._check(expense, approver, limit)
        if not reason or not reason.strip():
            raise Refused("rejection-has-reason")
        expense.state = REJECTED
        expense.reason = reason
        return Decision(expense.state, reason, True)
'''


if __name__ == "__main__":
    raise SystemExit(main())
