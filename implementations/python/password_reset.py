"""Deterministic reference runtime for the password-reset workflow."""

from dataclasses import dataclass, field
from typing import Literal


PERSON_CAPABILITY = "person.request-password-reset"
SEND_MESSAGE_CAPABILITY = "system.send-reset-message"
TOKEN_TTL_SECONDS = 15 * 60


class CapabilityDenied(Exception):
    """Raised when a workflow lacks a required capability."""


class TokenRejected(Exception):
    """Raised when a reset token is expired or has already been used."""


@dataclass
class AccountStore:
    existing_addresses: set[str]
    available: bool = True

    def lookup(self, email: str) -> bool:
        if not self.available:
            raise RuntimeError("account store unavailable")
        return email in self.existing_addresses


@dataclass
class EmailProvider:
    available: bool = True
    sent_messages: list[str] = field(default_factory=list)

    def send_reset_message(self, email: str) -> None:
        if not self.available:
            raise RuntimeError("email provider unavailable")
        self.sent_messages.append(email)


@dataclass
class ResetTokenStore:
    issued: dict[str, tuple[str, int]] = field(default_factory=dict)
    used: set[str] = field(default_factory=set)
    next_id: int = 1

    def issue(self, email: str, now: int) -> str:
        token = f"reset-token-{self.next_id}"
        self.next_id += 1
        self.issued[token] = (email, now)
        return token

    def redeem(self, token: str, now: int) -> str:
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
    response: Literal["standard-confirmation"]
    reset_message: Literal["sent", "not-sent"]
    account_existence_disclosed: bool
    recovery: str | None = None
    transitions: tuple[str, ...] = ()
    reset_token: str | None = None
    inputs: dict[str, str | int] = field(default_factory=dict)
    decisions: dict[str, str | bool] = field(default_factory=dict)
    state_changes: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    outputs: dict[str, str | bool] = field(default_factory=dict)
    failures: tuple[str, ...] = ()


class PasswordResetRuntime:
    """Execute request-reset against deterministic external-effect adapters."""

    def __init__(self, account_store: AccountStore, email_provider: EmailProvider, token_store: ResetTokenStore | None = None):
        self.account_store = account_store
        self.email_provider = email_provider
        self.token_store = token_store or ResetTokenStore()

    def request_reset(self, email: str, capabilities: set[str], now: int = 0) -> ResetResult:
        if PERSON_CAPABILITY not in capabilities:
            raise CapabilityDenied(PERSON_CAPABILITY)

        transitions = ["request received", "request normalized", "account lookup performed"]
        inputs = {"email": email, "now": now}
        effects = ["account-store.lookup"]
        try:
            account_exists = self.account_store.lookup(email)
        except RuntimeError:
            return ResetResult(
                "standard-confirmation", "not-sent", False,
                "no-account-state-disclosed",
                tuple(transitions + ["standard response returned"]),
                inputs=inputs,
                decisions={"account_exists": "unknown"},
                state_changes=("request-received",),
                effects=tuple(effects),
                outputs={"response": "standard-confirmation", "accountExistenceDisclosed": False},
                failures=("account-store.unavailable",),
            )

        if not account_exists:
            transitions.append("reset token conditionally created")
            return ResetResult(
                "standard-confirmation", "not-sent", False,
                transitions=tuple(transitions + ["standard response returned"]),
                inputs=inputs,
                decisions={"account_exists": False, "issue_token": False},
                state_changes=("request-received", "request-normalized"),
                effects=tuple(effects),
                outputs={"response": "standard-confirmation", "resetMessage": "not-sent", "accountExistenceDisclosed": False},
            )

        if SEND_MESSAGE_CAPABILITY not in capabilities:
            raise CapabilityDenied(SEND_MESSAGE_CAPABILITY)
        reset_token = self.token_store.issue(email, now)
        transitions.append("reset token created")
        effects.append("reset-token.issue")
        try:
            self.email_provider.send_reset_message(email)
        except RuntimeError:
            effects.append("email-provider.send-reset-message")
            return ResetResult(
                "standard-confirmation", "not-sent", False,
                "no-account-state-disclosed",
                tuple(transitions + ["standard response returned"]),
                reset_token,
                inputs=inputs,
                decisions={"account_exists": True, "issue_token": True, "send_message": False},
                state_changes=("request-received", "request-normalized", "reset-token-issued"),
                effects=tuple(effects),
                outputs={"response": "standard-confirmation", "resetMessage": "not-sent", "accountExistenceDisclosed": False},
                failures=("email-provider.unavailable",),
            )
        effects.append("email-provider.send-reset-message")
        return ResetResult(
            "standard-confirmation", "sent", False,
            transitions=tuple(transitions + ["reset message conditionally sent", "standard response returned"]),
            reset_token=reset_token,
            inputs=inputs,
            decisions={"account_exists": True, "issue_token": True, "send_message": True},
            state_changes=("request-received", "request-normalized", "reset-token-issued", "reset-message-sent"),
            effects=tuple(effects),
            outputs={"response": "standard-confirmation", "resetMessage": "sent", "accountExistenceDisclosed": False},
        )

    def redeem_reset(self, token: str, now: int) -> str:
        return self.token_store.redeem(token, now)

    def request_resets_concurrently(
        self, emails: list[str], capabilities: set[str], now: int = 0
    ) -> tuple[ResetResult, ...]:
        """Run concurrent requests through a deterministic input-order scheduler."""
        return tuple(self.request_reset(email, capabilities, now) for email in emails)