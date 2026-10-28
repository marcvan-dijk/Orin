import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, generatePasswordReset } from "./generate_password_reset.ts";

const ROOT = resolve(fileURLToPath(new URL("../../../..", import.meta.url)));
const load = (name: string) => JSON.parse(readFileSync(resolve(ROOT, "tests/conformance", name), "utf-8"));
const decision = { maxRequests: 3, windowSeconds: 600 };

let seq = 0;

async function loadGenerated(model: SemanticModel) {
  const source = generatePasswordReset(model, decision);
  const dir = resolve(fileURLToPath(new URL(".", import.meta.url)), ".generated");
  mkdirSync(dir, { recursive: true });
  const file = resolve(dir, `password_reset_${++seq}.ts`);
  writeFileSync(file, source);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test("generation is deterministic", () => {
  const model = new SemanticModel(load("password-reset.model.json"));
  assert.equal(generatePasswordReset(model, decision), generatePasswordReset(model, decision));
});

test("refuses blocked models and invalid decisions", () => {
  const blocked = new SemanticModel(load("shared-tasks.rule-contradiction-multi.model.json"));
  assert.throws(() => generatePasswordReset(blocked, decision), GenerationRefused);
  const model = new SemanticModel(load("password-reset.model.json"));
  assert.throws(() => generatePasswordReset(model, { maxRequests: 0, windowSeconds: 1 }), GenerationRefused);
});

test("generated module satisfies password-reset conformance cases", async () => {
  const gen = await loadGenerated(new SemanticModel(load("password-reset.model.json")));
  const cases = load("password-reset.cases.json").cases.filter((c: any) => c.when.action !== "compile");
  assert.ok(cases.length > 0);
  for (const c of cases) {
    const g = c.given;
    const exists = (email: string) => {
      if (g.accountStore === "unavailable") throw new Error("account-store.unavailable");
      return Boolean(g.accountExists) && email === "person@example.com";
    };
    const ports = {
      accountExists: exists,
      sendResetMessage: () => {
        if (g.emailProvider === "unavailable") throw new Error("email-provider.unavailable");
      },
    };
    const rt = new gen.PasswordReset(ports);
    const email = "person@example.com";
    let actual: Record<string, any>;
    switch (c.when.action) {
      case "request-password-reset":
        actual = rt.requestReset(email);
        break;
      case "request-password-reset-twice":
      case "request-password-reset-concurrently": {
        const rs = [rt.requestReset(email), rt.requestReset(email)];
        actual = { tokensDistinct: rs[0].resetToken !== rs[1].resetToken, responses: rs.map((r: any) => r.response) };
        break;
      }
      case "redeem-expired-token": {
        const r = rt.requestReset(email, 0);
        actual = { token: "rejected", reason: (() => { try { rt.redeemReset(r.resetToken, 900); } catch (e: any) { return e.message; } })() };
        break;
      }
      case "redeem-token-twice": {
        const r = rt.requestReset(email, 0);
        rt.redeemReset(r.resetToken, 1);
        actual = { token: "rejected", reason: (() => { try { rt.redeemReset(r.resetToken, 2); } catch (e: any) { return e.message; } })() };
        break;
      }
      default:
        assert.fail(`unsupported action ${c.when.action} in ${c.id}`);
    }
    for (const [key, value] of Object.entries(c.then)) {
      assert.deepEqual(actual[key], value, `${c.id}: ${key}`);
    }
  }
});

test("generated module enforces the resolved rate limit", async () => {
  const gen = await loadGenerated(new SemanticModel(load("password-reset.model.json")));
  const rt = new gen.PasswordReset({ accountExists: () => true, sendResetMessage: () => {} });
  const tokens = [0, 1, 2, 3].map((t) => rt.requestReset("a@example.com", t).resetToken);
  assert.deepEqual(tokens.map(Boolean), [true, true, true, false]);
  assert.equal(rt.requestReset("a@example.com", 600).resetToken !== "", true);
});
