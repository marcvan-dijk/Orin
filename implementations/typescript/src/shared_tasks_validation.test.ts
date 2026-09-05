import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { SemanticModel } from "./orin_model.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const VALIDATION_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.validation-cases.json");
const READINESS_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.readiness-partial.model.json");

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
}

test("shared-tasks validation fixtures assert diagnostics parity", async (t) => {
  const fixture = loadJson(VALIDATION_FIXTURE);

  for (const validationCase of fixture.cases || []) {
    await t.test(validationCase.id, () => {
      const modelPath = resolve(ROOT, "tests/conformance", validationCase.model);
      const model = new SemanticModel(loadJson(modelPath));
      const diagnostics = model.diagnostics();
      const actual = {
        compilation: model.compilationStatus(),
        diagnostics: diagnostics.map((diagnostic) => diagnostic.code).sort(),
        diagnosticEntries: diagnostics.map((diagnostic) => ({
          code: diagnostic.code,
          objectId: diagnostic.objectId ?? null,
          message: diagnostic.message,
        })),
      };
      const expectedDiagnostics = [...(validationCase.then?.diagnostics || [])].sort();
      for (const code of [...expectedDiagnostics, ...actual.diagnostics]) {
        assert.match(code, /^ORIN-E\d{3}$/);
      }
      assert.equal(actual.compilation, validationCase.then?.compilation);
      assert.deepEqual(actual.diagnostics, expectedDiagnostics);
      if (validationCase.then?.diagnosticEntries) {
        assert.deepEqual(actual.diagnosticEntries, validationCase.then.diagnosticEntries);
      }
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

test("rule contradiction diagnostic mirrors Python semantics for not-prefix claims", () => {
  const model = new SemanticModel(loadJson(resolve(ROOT, "tests/conformance/shared-tasks.rule-contradiction-negated.model.json")));
  assert.deepEqual(model.diagnostics().map((diagnostic) => diagnostic.code), ["ORIN-E046"]);
  assert.equal(model.compilationStatus(), "fail");
});

test("rule contradiction diagnostic mirrors Python semantics for structured negation flags", () => {
  const model = new SemanticModel(loadJson(resolve(ROOT, "tests/conformance/shared-tasks.rule-contradiction-not-prefix.model.json")));
  assert.deepEqual(model.diagnostics().map((diagnostic) => diagnostic.code), ["ORIN-E046"]);
  assert.equal(model.compilationStatus(), "fail");
});

test("rule contradiction diagnostics stay deterministic for multi-claim contradictions", () => {
  const model = new SemanticModel({
    modelVersion: "0.1.0",
    module: { id: "shared-tasks/module", kind: "module", name: "shared-tasks", status: "accepted" },
    objects: [
      {
        id: "shared-tasks/rule/member-completion",
        kind: "rule",
        name: "member-completion",
        status: "accepted",
        claims: [
          "Task title must be non-empty.",
          "not Task title must be non-empty.",
          { text: "Assignee must be a list member.", negated: false },
          { text: "Assignee must be a list member.", negated: true },
        ],
      },
    ],
  });

  const contradictions = model
    .diagnostics()
    .filter((diagnostic) => diagnostic.code === "ORIN-E046")
    .map((diagnostic) => ({
      objectId: diagnostic.objectId,
      message: diagnostic.message,
    }));

  assert.deepEqual(contradictions, [
    {
      objectId: "shared-tasks/rule/member-completion",
      message: "rule contains contradictory claims: assignee must be a list member",
    },
    {
      objectId: "shared-tasks/rule/member-completion",
      message: "rule contains contradictory claims: task title must be non-empty",
    },
  ]);
  assert.equal(model.compilationStatus(), "fail");
});

test("readiness report is deterministic for a partially complete model", () => {
  const report = new SemanticModel(loadJson(READINESS_FIXTURE)).readinessReport();
  assert.equal(report.schemaVersion, "0.1.0");
  assert.equal(report.status, "blocked");
  assert.equal(report.validationStatus, "eligible");
  assert.deepEqual(
    report.diagnostics.map((diagnostic) => ({
      code: diagnostic.code,
      category: diagnostic.category,
      blocking: diagnostic.blocking,
      path: diagnostic.path,
    })),
    [
      {
        code: "ORIN-R001",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1capability~1complete-task/owner",
      },
      {
        code: "ORIN-R002",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1capability~1complete-task/scope",
      },
      {
        code: "ORIN-R010",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1effect~1persistent-entity-store.write.task-state/failureModes",
      },
      {
        code: "ORIN-R020",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1workflow~1complete-task/failureBehavior",
      },
      {
        code: "ORIN-R101",
        category: "optional-default",
        blocking: false,
        path: "/objects/shared-tasks~1relation~1assigned-to/deletionBehavior",
      },
      {
        code: "ORIN-R102",
        category: "optional-default",
        blocking: false,
        path: "/objects/shared-tasks~1effect~1persistent-entity-store.write.task-state/retryPolicy",
      },
      {
        code: "ORIN-R201",
        category: "unresolved-assumption",
        blocking: false,
        path: "/objects/shared-tasks~1uncertainty~1audit-retention",
      },
      {
        code: "ORIN-R301",
        category: "implementation-preference",
        blocking: false,
        path: "/module/implementationPolicies/optimize-for",
      },
    ],
  );
});

test("readiness affected-object paths preserve downstream references", () => {
  const report = new SemanticModel(loadJson(READINESS_FIXTURE)).readinessReport();
  const ownerGap = report.diagnostics.find((diagnostic) => diagnostic.code === "ORIN-R001");
  assert.ok(ownerGap);
  assert.equal(ownerGap.objectId, "shared-tasks/capability/complete-task");
  assert.deepEqual(ownerGap.affectedObjectPaths, [
    "/objects/shared-tasks~1capability~1complete-task",
    "/objects/shared-tasks~1workflow~1complete-task",
    "/objects/shared-tasks~1example~1successful-completion",
    "/objects/shared-tasks~1target~1web-service",
    "/objects/shared-tasks~1uncertainty~1audit-retention",
  ]);
});
