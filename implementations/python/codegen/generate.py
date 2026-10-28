"""Generate a standalone Python module from a ready password-reset Orin model.

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


def _object(model: SemanticModel, object_id: str) -> dict:
    for obj in model.document.get("objects", []):
        if isinstance(obj, dict) and obj.get("id") == object_id:
            return obj
    raise GenerationError(f"model is missing required object: {object_id}")


def _ttl_seconds(model: SemanticModel) -> int:
    for claim in _object(model, EXPIRY_RULE_ID).get("claims", []):
        match = re.search(r"expire after (\d+) (second|minute|hour)s?", claim)
        if match:
            return int(match.group(1)) * _UNITS[match.group(2)]
    raise GenerationError(f"cannot derive token lifetime from {EXPIRY_RULE_ID}")


def _rate_limit(model: SemanticModel) -> tuple[int, int, bool]:
    """Return (max attempts, window seconds, per network origin) from the accepted rule."""
    for claim in _object(model, RATE_LIMIT_RULE_ID).get("claims", []):
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
    return model.document.get("module", {}).get("id") == EXPENSE_MODULE_ID


def output_name(model: SemanticModel) -> str:
    return EXPENSE_OUTPUT_NAME if _is_expense(model) else OUTPUT_NAME


def generate_source(model: SemanticModel) -> str:
    gates = model.compute_readiness_gates()
    if gates["compilation"] != "eligible":
        blockers = ", ".join(gates.get("blockingUnresolved", [])) or "diagnostics present"
        raise GenerationError(
            f"model is not ready for generation (compilation={gates['compilation']}): {blockers}. "
            "Resolve the consequential decisions first."
        )
    module_id = model.document.get("module", {}).get("id", "unknown")
    if _is_expense(model):
        for object_id in (EXPENSE_WORKFLOW_ID, *EXPENSE_RULES):
            _object(model, object_id)
        return _EXPENSE_TEMPLATE.replace("@@MODULE@@", json.dumps(module_id))
    _object(model, WORKFLOW_ID)
    _object(model, SINGLE_USE_RULE_ID)
    _object(model, NO_DISCLOSURE_RULE_ID)
    limit, window, per_origin = _rate_limit(model)
    return (
        _TEMPLATE.replace("@@MODULE@@", json.dumps(module_id))
        .replace("@@TTL@@", str(_ttl_seconds(model)))
        .replace("@@RATE_LIMIT@@", str(limit))
        .replace("@@RATE_WINDOW@@", str(window))
        .replace("@@RATE_PER_ORIGIN@@", str(per_origin))
    )


def generate(model_path: str | Path, outdir: str | Path) -> Path:
    model = SemanticModel.from_json_file(model_path)
    source = generate_source(model)
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    target = out / output_name(model)
    target.write_text(source, encoding="utf-8", newline="\n")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a Python implementation from a ready Orin model.")
    parser.add_argument("model", help="path to a semantic model JSON file")
    parser.add_argument("outdir", help="directory to write the generated module into")
    args = parser.parse_args(argv)
    try:
        target = generate(args.model, args.outdir)
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
