import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { executeCase } from "./conformance_runner.ts";
import { SemanticModel } from "./orin_model.ts";
import { runDerivationProof } from "./password_reset_proof.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const MODEL_FIXTURE = resolve(ROOT, "tests/conformance/password-reset.model.json");
const CASES_FIXTURE = resolve(ROOT, "tests/conformance/password-reset.cases.json");

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function resolveRateLimit(model: SemanticModel): SemanticModel {
  const next = JSON.parse(JSON.stringify(model.document));
  for (const obj of next.objects || []) {
    if (obj.kind === "uncertainty" && obj.id === "account.password-reset/uncertainty/rate-limit") {
      obj.status = "resolved";
    }
  }
  return new SemanticModel(next);
}

test("derivation proof remains aligned with conformance behavior cases", () => {
  const proof = runDerivationProof();
  const casesFixture = loadJson(CASES_FIXTURE);
  const expectedBehaviorCases = (casesFixture.cases || [])
    .filter((conformanceCase: Record<string, any>) => conformanceCase?.when?.action !== "compile")
    .map((conformanceCase: Record<string, any>) => conformanceCase.id);

  assert.equal(proof.blockedCompilation, "blocked");
  assert.equal(proof.resolvedCompilation, "eligible");
  assert.equal(proof.canonicalMeaningStableAcrossVariants, true);
  assert.ok(Array.isArray(proof.variants));
  assert.ok(proof.variants.length >= 2);
  assert.notDeepEqual(proof.variants[0].derivedArtifact, proof.variants[1].derivedArtifact);
  assert.deepEqual(proof.behaviorCases, expectedBehaviorCases);
});

test("resolved model executes every non-compile conformance assertion", () => {
  const model = resolveRateLimit(new SemanticModel(loadJson(MODEL_FIXTURE)));
  const casesFixture = loadJson(CASES_FIXTURE);

  for (const conformanceCase of casesFixture.cases || []) {
    if (conformanceCase?.when?.action === "compile") {
      continue;
    }
    const actual = executeCase(model, conformanceCase);
    for (const [key, expected] of Object.entries(conformanceCase.then || {})) {
      assert.deepEqual(actual[key], expected, `case ${conformanceCase.id} mismatch for '${key}'`);
    }
  }
});
