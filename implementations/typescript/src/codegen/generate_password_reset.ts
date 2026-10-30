import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, checkedModuleId, readiness } from "./sanitize.ts";

export const RATE_LIMIT_UNCERTAINTY = "account.password-reset/uncertainty/rate-limit";

export type RateLimitDecision = {
  maxRequests: number;
  windowSeconds: number;
  scope?: "address" | "address-and-origin";
};

function acceptedDecision(model: SemanticModel): RateLimitDecision {
  const rule = model.document.objects?.find(
    (object: any) => object.id === "account.password-reset/rule/reset-request-rate-limit",
  );
  if (rule?.status === "accepted" && Array.isArray(rule.claims)) {
    for (const claim of rule.claims) {
      if (typeof claim !== "string") continue;
      const match = /^Password reset requests are limited to (\d+) attempts? per (?:(\d+) )?(second|minute|hour)s? for the same email address( and network origin\.|, regardless of network origin\.)$/.exec(claim);
      if (!match) continue;
      const units = { second: 1, minute: 60, hour: 3600 };
      return {
        maxRequests: Number(match[1]),
        windowSeconds: Number(match[2] ?? 1) * units[match[3] as keyof typeof units],
        scope: match[4].includes("and network origin") ? "address-and-origin" : "address",
      };
    }
  }
  throw new GenerationRefused("cannot derive rate limit from accepted reset-request-rate-limit rule");
}

export { GenerationRefused };

function resolved(model: SemanticModel): SemanticModel {
  const next = JSON.parse(JSON.stringify(model.document));
  if (Array.isArray(next.unresolved)) {
    next.unresolved = next.unresolved.filter((id: unknown) => id !== RATE_LIMIT_UNCERTAINTY);
  }
  return new SemanticModel(next);
}

// Emits a standalone, dependency-free TypeScript module. Output is a pure
// function of (model identity, decision) and contains no timestamps.
export function generatePasswordReset(model: SemanticModel, decision?: RateLimitDecision | null): string {
  decision ??= acceptedDecision(model);
  if (!Number.isInteger(decision?.maxRequests) || decision.maxRequests < 1
    || !Number.isInteger(decision?.windowSeconds) || decision.windowSeconds < 1) {
    throw new GenerationRefused("rate-limit decision requires positive integer maxRequests and windowSeconds");
  }
  if (decision.scope !== undefined && decision.scope !== "address" && decision.scope !== "address-and-origin") {
    throw new GenerationRefused("unsupported rate-limit scope");
  }
  const moduleId = checkedModuleId(model);
  const gates = readiness(resolved(model));
  if (gates.compilation !== "eligible") {
    throw new GenerationRefused(
      `model is ${gates.compilation}; unresolved: ${gates.blockingUnresolved.join(", ") || "none"}`,
    );
  }
  return `// Generated from ${moduleId}. Do not edit.
// Resolved ${RATE_LIMIT_UNCERTAINTY}: ${decision.maxRequests} requests per ${decision.windowSeconds}s per ${decision.scope ?? "address"}.

export const RATE_LIMIT = { maxRequests: ${decision.maxRequests}, windowSeconds: ${decision.windowSeconds} } as const;
export const RATE_LIMIT_PER_ORIGIN = ${decision.scope === "address-and-origin"};
export const TOKEN_TTL_SECONDS = 15 * 60;

export class TokenRejected extends Error {}

export interface Ports {
  accountExists(email: string): boolean;
  sendResetMessage(email: string): void;
}

export interface ResetResult {
  response: "standard-confirmation";
  resetMessage: "sent" | "not-sent";
  accountExistenceDisclosed: false;
  recovery?: "no-account-state-disclosed";
  resetToken: string;
}

export class PasswordReset {
  private counter = 0;
  private tokens = new Map<string, { email: string; expiresAt: number; used: boolean }>();
  private hits = new Map<string, number[]>();

  private ports: Ports;

  constructor(ports: Ports) {
    this.ports = ports;
  }

  requestReset(email: string, now = 0, origin = ""): ResetResult {
    const result: ResetResult = {
      response: "standard-confirmation",
      resetMessage: "not-sent",
      accountExistenceDisclosed: false,
      resetToken: "",
    };
    const key = JSON.stringify(RATE_LIMIT_PER_ORIGIN ? [email, origin] : [email]);
    const recent = (this.hits.get(key) ?? []).filter((t) => now - t < RATE_LIMIT.windowSeconds);
    if (recent.length >= RATE_LIMIT.maxRequests) {
      this.hits.set(key, recent);
      return result;
    }
    recent.push(now);
    this.hits.set(key, recent);

    let exists = false;
    try {
      exists = this.ports.accountExists(email);
    } catch {
      result.recovery = "no-account-state-disclosed";
      return result;
    }
    if (!exists) return result;
    result.resetToken = \`token-\${++this.counter}\`;
    this.tokens.set(result.resetToken, { email, expiresAt: now + TOKEN_TTL_SECONDS, used: false });
    try {
      this.ports.sendResetMessage(email);
      result.resetMessage = "sent";
    } catch {
      result.recovery = "no-account-state-disclosed";
    }
    return result;
  }

  redeemReset(token: string, now: number): string {
    const record = this.tokens.get(token);
    if (!record) throw new TokenRejected("token missing");
    if (now >= record.expiresAt) throw new TokenRejected("token expired");
    if (record.used) throw new TokenRejected("token already used");
    record.used = true;
    return record.email;
  }
}
`;
}

if (import.meta.main) {
  const { readFileSync } = await import("node:fs");
  const [path, max = "5", window = "3600"] = process.argv.slice(2);
  if (!path) throw new Error("usage: generate_password_reset.ts <model.json> [maxRequests] [windowSeconds]");
  process.stdout.write(generatePasswordReset(SemanticModel.fromJsonText(readFileSync(path, "utf-8")), {
    maxRequests: Number(max),
    windowSeconds: Number(window),
  }));
}
