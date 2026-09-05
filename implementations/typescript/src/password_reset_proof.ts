import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { executeCase } from "./conformance_runner.ts";
import { lower } from "./lowering.ts";
import { SemanticModel } from "./orin_model.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
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

function deepEqual(left: unknown, right: unknown): boolean {
  if (left === right) {
    return true;
  }
  if (typeof left !== "object" || left === null || typeof right !== "object" || right === null) {
    return false;
  }
  if (Array.isArray(left) || Array.isArray(right)) {
    if (!Array.isArray(left) || !Array.isArray(right) || left.length !== right.length) {
      return false;
    }
    return left.every((item, index) => deepEqual(item, right[index]));
  }
  const leftEntries = Object.entries(left as Record<string, unknown>);
  const rightEntries = Object.entries(right as Record<string, unknown>);
  if (leftEntries.length !== rightEntries.length) {
    return false;
  }
  const rightMap = new Map<string, unknown>(rightEntries);
  return leftEntries.every(([key, value]) => rightMap.has(key) && deepEqual(value, rightMap.get(key)));
}

function behaviorResults(model: SemanticModel, casesFixture: Record<string, any>): Array<Record<string, any>> {
  const results: Array<Record<string, any>> = [];
  for (const conformanceCase of casesFixture.cases || []) {
    if (conformanceCase?.when?.action === "compile") {
      continue;
    }
    const actual = executeCase(model, conformanceCase);
    for (const [key, expected] of Object.entries(conformanceCase.then || {})) {
      if (!deepEqual(actual[key], expected)) {
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

function isDirectExecution(): boolean {
  const entry = process.argv[1];
  return !!entry && import.meta.url === pathToFileURL(resolve(entry)).href;
}

if (isDirectExecution()) {
  console.log(JSON.stringify(runDerivationProof(), null, 2));
}
