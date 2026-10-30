import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { SemanticModel } from "../orin_model.ts";
import { RATE_LIMIT_UNCERTAINTY } from "./generate_password_reset.ts";
import { generate } from "./cli.ts";

export const DEFAULT_FIXTURE = fileURLToPath(
  new URL("../../../../tests/conformance/password-reset.rate-limit.cases.json", import.meta.url),
);
const MODEL_PATH = fileURLToPath(new URL("../../../../tests/conformance/password-reset.model.json", import.meta.url));

// These are the accepted rule claims emitted by OrinDecisionAgent.apply_decision.
// The generator, not the replayer, derives the window, count and key from them.
const ACCEPTED_CLAIMS: Record<string, string> = {
  "five-per-15m-per-address-and-origin":
    "Password reset requests are limited to 5 attempts per 15 minutes for the same email address and network origin.",
  "three-per-hour-per-address":
    "Password reset requests are limited to 3 attempts per hour for the same email address, regardless of network origin.",
};

export type Observables = {
  responses: string[];
  resetMessages: string[];
  accountExistenceDisclosed: boolean[];
};
export type RateLimitResults = Record<string, Record<string, Observables>>;

type Fixture = {
  fixtureVersion: string;
  uncertainty: string;
  policies: { id: string }[];
  cases: {
    id: string;
    given: { existingAddresses: string[] };
    when: { requests: { email: string; origin: string; at: number }[] };
    then: Record<string, Observables>;
  }[];
};

export function acceptedPolicyModel(policyId: string): SemanticModel {
  assert.ok(Object.hasOwn(ACCEPTED_CLAIMS, policyId), `unsupported rate-limit policy: ${policyId}`);
  const document = JSON.parse(readFileSync(MODEL_PATH, "utf-8"));
  document.unresolved = document.unresolved.filter((id: string) => id !== RATE_LIMIT_UNCERTAINTY);
  document.objects.push({
    id: "account.password-reset/rule/reset-request-rate-limit",
    kind: "rule",
    name: "reset-request-rate-limit",
    status: "accepted",
    claims: [
      ACCEPTED_CLAIMS[policyId],
      "Requests rejected by the rate limit return the same standard confirmation without revealing account existence.",
    ],
  });
  return new SemanticModel(document);
}

export async function runFixture(fixturePath: string = DEFAULT_FIXTURE): Promise<RateLimitResults> {
  const fixture: Fixture = JSON.parse(readFileSync(fixturePath, "utf-8"));
  assert.equal(fixture.fixtureVersion, "0.1.0", "unsupported fixture version");
  assert.equal(fixture.uncertainty, RATE_LIMIT_UNCERTAINTY);
  assert.ok(fixture.cases.length > 0, "rate-limit fixture must not be empty");
  const policyIds = fixture.policies.map((policy) => policy.id);
  for (const id of policyIds) {
    assert.ok(Object.hasOwn(ACCEPTED_CLAIMS, id), `unsupported rate-limit policy: ${id}`);
  }
  assert.deepEqual([...policyIds].sort(), Object.keys(ACCEPTED_CLAIMS).sort(), "both accepted policies are required");
  assert.equal(new Set(fixture.cases.map((c) => c.id)).size, fixture.cases.length, "duplicate case IDs");
  assert.ok(fixture.cases.some((c) => {
    return JSON.stringify(c.then[policyIds[0]]) !== JSON.stringify(c.then[policyIds[1]]);
  }), "fixture must distinguish the accepted policies");

  const results: RateLimitResults = {};
  const directory = mkdtempSync(fileURLToPath(new URL(".rate-limit-generated-", import.meta.url)));
  try {
    for (const policyId of policyIds) {
      const model = acceptedPolicyModel(policyId);
      // JSON null lets the public CLI dispatcher use the accepted model decision.
      const output = generate(JSON.stringify(model.document), "null");
      const path = join(directory, `${policyId}.ts`);
      writeFileSync(path, output.source);
      const generated = await import(pathToFileURL(path).href);
      const policyResults: Record<string, Observables> = {};
      results[policyId] = policyResults;
      for (const c of fixture.cases) {
        assert.deepEqual(Object.keys(c.then).sort(), [...policyIds].sort(), `${c.id}: policy expectations`);
        assert.ok(c.when.requests.length > 0, `${c.id}: requests must not be empty`);
        const addresses = new Set(c.given.existingAddresses);
        const sent: string[] = [];
        const runtime = new generated.PasswordReset({
          accountExists: (email: string) => addresses.has(email),
          sendResetMessage: (email: string) => { sent.push(email); },
        });
        const actual: Observables = { responses: [], resetMessages: [], accountExistenceDisclosed: [] };
        let previousTime = -Infinity;
        for (const request of c.when.requests) {
          assert.equal(typeof request.email, "string", `${c.id}: email`);
          assert.equal(typeof request.origin, "string", `${c.id}: origin`);
          assert.ok(Number.isInteger(request.at) && request.at >= previousTime, `${c.id}: ordered integer seconds`);
          previousTime = request.at;
          const before = sent.length;
          const result = runtime.requestReset(request.email, request.at, request.origin);
          assert.equal(sent.length - before, result.resetMessage === "sent" ? 1 : 0, `${c.id}: message side effect`);
          actual.responses.push(result.response);
          actual.resetMessages.push(result.resetMessage);
          actual.accountExistenceDisclosed.push(result.accountExistenceDisclosed);
        }
        assert.deepEqual(actual, c.then[policyId], `${policyId}: ${c.id}`);
        policyResults[c.id] = actual;
      }
    }
    return results;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

if (import.meta.main) {
  assert.ok(process.argv.length <= 3, "usage: password_reset_rate_limit.ts [fixture_path]");
  process.stdout.write(`${JSON.stringify(await runFixture(process.argv[2]))}\n`);
}
