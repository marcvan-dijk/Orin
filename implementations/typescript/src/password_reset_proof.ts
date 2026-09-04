import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { executeCase } from "./conformance_runner";
import { lower } from "./lowering";
import { SemanticModel } from "./orin_model";

const ROOT = resolve(__dirname, "..", "..", "..");
const MODEL_FIXTURE = resolve(ROOT, "tests/conformance/password-reset.model.json");
const CASES_FIXTURE = resolve(ROOT, "tests/conformance/password-reset.cases.json");
const POLICIES_FIXTURE = resolve(ROOT, "tests/conformance/password-reset.policies.json");

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

function behaviorResults(model: SemanticModel, casesFixture: Record<string, any>): Array<Record<string, any>> {
  const results: Array<Record<string, any>> = [];
  for (const conformanceCase of casesFixture.cases || []) {
    if (conformanceCase?.when?.action === "compile") {
      continue;
    }
    const actual = executeCase(model, conformanceCase);
    for (const [key, expected] of Object.entries(conformanceCase.then || {})) {
      if (actual[key] !== expected) {
        throw new Error(`case ${conformanceCase.id} mismatch for '${key}'`);
      }
    }
    results.push({ id: conformanceCase.id });
  }
  return results;
}

export function runDerivationProof(): Record<string, any> {
  const blockedModel = new SemanticModel(loadJson(MODEL_FIXTURE));
  const casesFixture = loadJson(CASES_FIXTURE);
  const policiesFixture = loadJson(POLICIES_FIXTURE);
  const variants = policiesFixture.variants || [];
  if (variants.length < 2) {
    throw new Error("proof requires at least two policy variants");
  }

  const blockedCase = (casesFixture.cases || []).find(
    (item: Record<string, any>) => item?.when?.action === "compile" && item?.then?.compilation === "blocked",
  );
  if (!blockedCase) {
    throw new Error("cases fixture must include blocked compile case");
  }

  const blockedCompilation = executeCase(blockedModel, blockedCase).compilation;
  const resolvedModel = resolveRateLimit(blockedModel);
  const resolvedCompilation = resolvedModel.compilationStatus();
  if (resolvedCompilation !== "eligible") {
    throw new Error(`resolved model should be eligible, got ${resolvedCompilation}`);
  }

  const variantOutputs = variants.map((variant: Record<string, any>) => {
    const document = JSON.parse(JSON.stringify(resolvedModel.document));
    document.module = document.module || {};
    document.module.implementationPolicies = variant.implementationPolicies;
    const variantModel = new SemanticModel(document);
    const lowered = lower(variantModel);
    if (!lowered.artifact) {
      throw new Error(`variant ${variant.id} lowering must include artifact`);
    }
    return {
      id: variant.id,
      derivedArtifact: lowered.artifact,
      canonical: variantModel.canonical(),
      behavior: behaviorResults(variantModel, casesFixture),
    };
  });

  const firstBehavior = JSON.stringify(variantOutputs[0].behavior);
  if (!firstBehavior) {
    throw new Error("cases fixture must include behavior cases");
  }
  if (!variantOutputs.every((item) => JSON.stringify(item.behavior) === firstBehavior)) {
    throw new Error("observable behavior should remain equal across policy variants");
  }
  if (new Set(variantOutputs.map((item) => JSON.stringify(item.derivedArtifact))).size < 2) {
    throw new Error("derived artifacts should differ across policy variants");
  }
  if (!variantOutputs.every((item) => JSON.stringify(item.canonical) === JSON.stringify(variantOutputs[0].canonical))) {
    throw new Error("canonical meaning should remain stable across policy variants");
  }

  return {
    blockedCompilation,
    resolvedCompilation,
    canonicalMeaningStableAcrossVariants: true,
    variants: variantOutputs.map((item) => ({
      id: item.id,
      derivedArtifact: item.derivedArtifact,
    })),
    behaviorCases: variantOutputs[0].behavior.map((item) => item.id),
  };
}
