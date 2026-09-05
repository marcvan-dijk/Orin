import { AccountStore, EmailProvider, PasswordResetRuntime, TokenRejected } from "./password_reset.ts";
import { SemanticModel } from "./orin_model.ts";

export function executeCase(model: SemanticModel, conformanceCase: Record<string, any>): Record<string, any> {
  const given = conformanceCase.given || {};
  const action = conformanceCase.when.action;
  if (action === "compile") {
    return { compilation: model.compilationStatus() };
  }

  const store = new AccountStore(new Set(given.accountExists ? ["person@example.com"] : []), (given.accountStore || "available") === "available");
  const emailProvider = new EmailProvider((given.emailProvider || "available") === "available");
  const runtime = new PasswordResetRuntime(store, emailProvider);
  const capabilities = new Set<string>(["person.request-password-reset", "system.send-reset-message"]);

  if (action === "request-password-reset") {
    return runtime.requestReset("person@example.com", capabilities);
  }
  if (action === "request-password-reset-twice") {
    const first = runtime.requestReset("person@example.com", capabilities);
    const second = runtime.requestReset("person@example.com", capabilities);
    return { tokensDistinct: first.resetToken !== second.resetToken, responses: [first.response, second.response] };
  }
  if (action === "request-password-reset-concurrently") {
    const results = runtime.requestResetsConcurrently(given.emails, capabilities);
    return {
      tokensDistinct: new Set(results.map((item) => item.resetToken)).size === results.length,
      responses: results.map((item) => item.response),
    };
  }
  if (action === "redeem-expired-token") {
    const result = runtime.requestReset("person@example.com", capabilities, 0);
    try {
      runtime.redeemReset(result.resetToken, 15 * 60);
    } catch (error) {
      if (error instanceof TokenRejected) {
        return { token: "rejected", reason: error.message };
      }
    }
  }
  if (action === "redeem-token-twice") {
    const result = runtime.requestReset("person@example.com", capabilities);
    runtime.redeemReset(result.resetToken, 1);
    try {
      runtime.redeemReset(result.resetToken, 2);
    } catch (error) {
      if (error instanceof TokenRejected) {
        return { token: "rejected", reason: error.message };
      }
    }
  }
  throw new Error(`unsupported conformance action: ${action}`);
}
