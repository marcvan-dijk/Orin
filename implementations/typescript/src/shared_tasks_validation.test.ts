import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { SemanticModel } from "./orin_model.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const VALIDATION_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.validation-cases.json");

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
}

test("shared-tasks validation fixtures assert diagnostics parity", async (t) => {
  const fixture = loadJson(VALIDATION_FIXTURE);

  for (const validationCase of fixture.cases || []) {
    await t.test(validationCase.id, () => {
      const modelPath = resolve(ROOT, "tests/conformance", validationCase.model);
      const model = new SemanticModel(loadJson(modelPath));
      const actual = {
        compilation: model.compilationStatus(),
        diagnostics: model.diagnostics().map((diagnostic) => diagnostic.code).sort(),
      };
      const expectedDiagnostics = [...(validationCase.then?.diagnostics || [])].sort();
      for (const code of [...expectedDiagnostics, ...actual.diagnostics]) {
        assert.match(code, /^ORIN-E\d{3}$/);
      }
      assert.equal(actual.compilation, validationCase.then?.compilation);
      assert.deepEqual(actual.diagnostics, expectedDiagnostics);
    });
  }
});

test("orphaned relation readiness diagnostic mirrors Python semantics", () => {
  const document = loadJson(resolve(ROOT, "tests/conformance/shared-tasks.model.json"));
  document.objects.push(
    {
      id: "shared-tasks/relation/participates-in",
      kind: "relation",
      name: "participates-in",
      status: "accepted",
      endpoints: [
        { type: "shared-tasks/entity-type/person" },
        { type: "shared-tasks/entity-type/task" },
      ],
      cardinality: "many-to-many",
    },
    {
      id: "shared-tasks/rule/task-list-membership-governance",
      kind: "rule",
      name: "task-list-membership-governance",
      status: "accepted",
      requires: ["shared-tasks/relation/member-of"],
    },
  );

  const model = new SemanticModel(document);
  assert.deepEqual(
    model.diagnostics().filter((diagnostic) => diagnostic.code === "ORIN-E045").map((diagnostic) => diagnostic.objectId),
    ["shared-tasks/relation/participates-in"],
  );
  assert.equal(model.compilationStatus(), "fail");
});
