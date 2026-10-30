import test from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { spawnSync } from "node:child_process";

import { SemanticModel } from "../orin_model.ts";
import { generate } from "./cli.ts";
import { GenerationRefused, generatePasswordReset } from "./generate_password_reset.ts";
import { acceptedPolicyModel, DEFAULT_FIXTURE, runFixture } from "./password_reset_rate_limit.ts";

const directory = fileURLToPath(new URL(".", import.meta.url));
const policyA = "five-per-15m-per-address-and-origin";
const policyB = "three-per-hour-per-address";
const loadFixture = () => JSON.parse(readFileSync(DEFAULT_FIXTURE, "utf-8"));

test("real generated TypeScript satisfies every rate-limit observable for both accepted policies", async () => {
  const fixture = loadFixture();
  assert.ok(fixture.cases.length > 0);
  assert.deepEqual(fixture.policies.map((p: any) => p.id).sort(), [policyA, policyB].sort());
  const before = readdirSync(directory).filter((name) => name.startsWith(".rate-limit-generated-"));
  const actual = await runFixture();
  for (const policy of fixture.policies) {
    assert.deepEqual(actual[policy.id], Object.fromEntries(fixture.cases.map((c: any) => [c.id, c.then[policy.id]])));
  }
  assert.ok(fixture.cases.some((c: any) => {
    return JSON.stringify(actual[policyA][c.id]) !== JSON.stringify(actual[policyB][c.id]);
  }), "the generated policies must observably differ");
  assert.deepEqual(readdirSync(directory).filter((name) => name.startsWith(".rate-limit-generated-")), before);
});

test("public generator derives count, window and origin scope from accepted rule claims", () => {
  const a = acceptedPolicyModel(policyA);
  const b = acceptedPolicyModel(policyB);
  const sourceA = generate(JSON.stringify(a.document), "null").source;
  const sourceB = generatePasswordReset(b);
  assert.match(sourceA, /maxRequests: 5, windowSeconds: 900/);
  assert.match(sourceA, /RATE_LIMIT_PER_ORIGIN = true/);
  assert.match(sourceB, /maxRequests: 3, windowSeconds: 3600/);
  assert.match(sourceB, /RATE_LIMIT_PER_ORIGIN = false/);
  const rule = a.document.objects.find((o: any) => o.name === "reset-request-rate-limit");
  rule.claims[0] = "Password reset requests are limited to 2 attempts per 10 seconds for the same email address and network origin.";
  assert.match(generatePasswordReset(a), /maxRequests: 2, windowSeconds: 10/);
  rule.status = "proposed";
  assert.throws(() => generatePasswordReset(a), GenerationRefused);
  assert.throws(() => generatePasswordReset(new SemanticModel(b.document), {
    maxRequests: 3, windowSeconds: 3600, scope: "unsupported" as any,
  }), /unsupported rate-limit scope/);
  assert.throws(() => acceptedPolicyModel("unsupported-policy"), /unsupported rate-limit policy/);
});

test("omitted decisions never default missing or unrecognized accepted rules, even in ready models", () => {
  const missingRule = acceptedPolicyModel(policyA).document;
  missingRule.objects = missingRule.objects.filter((o: any) => o.name !== "reset-request-rate-limit");
  const unknownRule = acceptedPolicyModel(policyA).document;
  unknownRule.objects.find((o: any) => o.name === "reset-request-rate-limit").claims = [
    "Use an unspecified abuse protection policy.",
  ];
  const arbitraryReady = { module: { id: "example.ready/module", name: "example.ready" }, objects: [], unresolved: [] };
  for (const document of [missingRule, unknownRule, arbitraryReady]) {
    for (const unresolved of [[], ["account.password-reset/uncertainty/rate-limit"]]) {
      const model = new SemanticModel({ ...document, unresolved });
      assert.throws(
        () => generatePasswordReset(model),
        (error: unknown) => error instanceof GenerationRefused && /cannot derive rate limit/.test(error.message),
      );
      if (model.document.module.id === "account.password-reset/module") {
        assert.throws(() => generate(JSON.stringify(model.document), "null"), GenerationRefused);
      }
    }
  }
  const generic = generate(JSON.stringify(arbitraryReady), "null");
  assert.doesNotMatch(generic.source, /class PasswordReset|RATE_LIMIT/);
});

test("generated runtime follows changed accepted count, window and origin claims without an override", async () => {
  const scratch = mkdtempSync(join(directory, ".rate-limit-test-"));
  try {
    for (const perOrigin of [true, false]) {
      const model = acceptedPolicyModel(policyA);
      model.document.objects.find((o: any) => o.name === "reset-request-rate-limit").claims[0] =
        "Password reset requests are limited to 2 attempts per 10 seconds for the same email address" +
        (perOrigin ? " and network origin." : ", regardless of network origin.");
      const path = join(scratch, `derived-${perOrigin}.ts`);
      writeFileSync(path, generate(JSON.stringify(model.document), "null").source);
      const generated = await import(pathToFileURL(path).href);
      const runtime = new generated.PasswordReset({
        accountExists: () => true,
        sendResetMessage: () => {},
      });
      const actual = [
        runtime.requestReset("person@example.com", 0, "one"),
        runtime.requestReset("person@example.com", 1, "one"),
        runtime.requestReset("person@example.com", 2, "one"),
        runtime.requestReset("person@example.com", 3, "two"),
        runtime.requestReset("other@example.com", 4, "one"),
        runtime.requestReset("person@example.com", 9, "one"),
        runtime.requestReset("person@example.com", 10, "one"),
      ].map((result) => result.resetMessage);
      assert.deepEqual(actual, [
        "sent", "sent", "not-sent", perOrigin ? "sent" : "not-sent", "sent", "not-sent", "sent",
      ]);
    }
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
});

test("runner rejects empty, unsupported and incorrect fixtures instead of skipping them", async () => {
  const scratch = mkdtempSync(join(directory, ".rate-limit-test-"));
  const path = join(scratch, "fixture.json");
  try {
    const empty = loadFixture();
    empty.cases = [];
    writeFileSync(path, JSON.stringify(empty));
    await assert.rejects(runFixture(path), /must not be empty/);

    const unsupported = loadFixture();
    unsupported.policies.push({ id: "unsupported-policy" });
    writeFileSync(path, JSON.stringify(unsupported));
    await assert.rejects(runFixture(path), /unsupported rate-limit policy/);

    const same = loadFixture();
    for (const c of same.cases) c.then[policyB] = c.then[policyA];
    writeFileSync(path, JSON.stringify(same));
    await assert.rejects(runFixture(path), /must distinguish/);

    const wrong = loadFixture();
    wrong.cases[0].then[policyA].resetMessages[0] = "incorrect";
    writeFileSync(path, JSON.stringify(wrong));
    await assert.rejects(runFixture(path), /five-per-15m-per-address-and-origin:/);
  } finally {
    rmSync(scratch, { recursive: true, force: true });
  }
});

test("CLI prints checked JSON results with the default or explicit fixture path", async () => {
  const expected = await runFixture();
  for (const args of [[], [DEFAULT_FIXTURE]]) {
    const child = spawnSync(process.execPath, [
      "--experimental-strip-types",
      fileURLToPath(new URL("password_reset_rate_limit.ts", import.meta.url)),
      ...args,
    ], { encoding: "utf-8" });
    assert.equal(child.status, 0, child.stderr);
    assert.deepEqual(JSON.parse(child.stdout), expected);
  }
});
