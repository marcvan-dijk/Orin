export class TokenRejected extends Error {}
export class CapabilityDenied extends Error {}

export class AccountStore {
  constructor(public accounts: Set<string>, public available = true) {}
  has(email: string): boolean {
    if (!this.available) {
      throw new Error("account-store.unavailable");
    }
    return this.accounts.has(email);
  }
}

export class EmailProvider {
  sentMessages: string[] = [];
  constructor(public available = true) {}
  send(email: string): void {
    if (!this.available) {
      throw new Error("email-provider.unavailable");
    }
    this.sentMessages.push(email);
  }
}

type TokenRecord = { email: string; expiresAt: number; used: boolean };

export class PasswordResetRuntime {
  private counter = 0;
  private tokens = new Map<string, TokenRecord>();

  constructor(public accountStore: AccountStore, public emailProvider: EmailProvider) {}

  requestReset(email: string, capabilities: Set<string>, now = 0): Record<string, any> {
    if (!capabilities.has("person.request-password-reset")) {
      throw new CapabilityDenied("missing capability");
    }
    let accountExists = false;
    let accountStoreFailed = false;
    try {
      accountExists = this.accountStore.has(email);
    } catch {
      accountStoreFailed = true;
    }

    let resetMessage: "sent" | "not-sent" = "not-sent";
    let recovery: string | undefined;
    let token = "";
    if (accountExists && !accountStoreFailed) {
      token = `token-${++this.counter}`;
      this.tokens.set(token, { email, expiresAt: now + 15 * 60, used: false });
      if (capabilities.has("system.send-reset-message")) {
        try {
          this.emailProvider.send(email);
          resetMessage = "sent";
        } catch {
          recovery = "no-account-state-disclosed";
        }
      }
    } else if (accountStoreFailed) {
      recovery = "no-account-state-disclosed";
    }

    return {
      response: "standard-confirmation",
      resetMessage,
      accountExistenceDisclosed: false,
      recovery,
      resetToken: token,
    };
  }

  requestResetsConcurrently(emails: string[], capabilities: Set<string>): Array<Record<string, any>> {
    return emails.map((email) => this.requestReset(email, capabilities));
  }

  redeemReset(token: string, now: number): string {
    const record = this.tokens.get(token);
    if (!record) {
      throw new TokenRejected("token missing");
    }
    if (now >= record.expiresAt) {
      throw new TokenRejected("token expired");
    }
    if (record.used) {
      throw new TokenRejected("token already used");
    }
    record.used = true;
    return record.email;
  }
}
