import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { SemanticModel } from "./orin_model.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const VALIDATION_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.validation-cases.json");
const READINESS_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.readiness-partial.model.json");
const READINESS_EXTENSION_CASES_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.readiness-extension-cases.json");
const READINESS_SCHEMA_FIXTURE = resolve(ROOT, "tests/conformance/readiness.schema.json");

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
  assert.equal(report.schemaVersion, loadJson(READINESS_SCHEMA_FIXTURE).schemaVersion);
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
        code: "ORIN-R030",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1entity-type~1task/lifecycle",
      },
      {
        code: "ORIN-R031",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1effect~1persistent-entity-store.write.task-state/inputs",
      },
      {
        code: "ORIN-R032",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1effect~1persistent-entity-store.write.task-state/outputs",
      },
      {
        code: "ORIN-R050",
        category: "required-decision",
        blocking: true,
        path: "/objects/shared-tasks~1workflow~1complete-task/postconditions",
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

test("readiness diagnostics cover 44D contract families with deterministic object/path parity", () => {
  const report = new SemanticModel({
    modelVersion: "0.1.0",
    module: { id: "contracts/module", kind: "module", name: "contracts", status: "accepted" },
    objects: [
      {
        id: "contracts/entity-type/task",
        kind: "entity-type",
        name: "task",
        status: "accepted",
        fields: [{ name: "id", type: "contracts/value-type/task-id", identity: true }],
      },
      { id: "contracts/value-type/task-id", kind: "value-type", name: "task-id", status: "accepted" },
      {
        id: "contracts/capability/write",
        kind: "capability",
        name: "write",
        status: "accepted",
        owner: "system",
        scope: "task-state",
      },
      {
        id: "contracts/effect/write-task",
        kind: "effect",
        name: "write-task",
        status: "accepted",
        requires: ["contracts/capability/write"],
        failureModes: ["unavailable"],
        dataAccess: ["task-state"],
        retryPolicy: "none",
      },
      {
        id: "contracts/rule/postcondition-proof",
        kind: "rule",
        name: "postcondition-proof",
        status: "accepted",
        claims: ["Task state update is observable."],
      },
      {
        id: "contracts/workflow/complete-task",
        kind: "workflow",
        name: "complete-task",
        status: "accepted",
        outputs: [{ name: "task", type: "contracts/entity-type/task" }],
        requires: ["contracts/capability/write"],
        uses: ["contracts/effect/write-task"],
        constrainedBy: ["contracts/rule/postcondition-proof"],
        failureBehavior: ["surface-effect-error"],
        recoveryBehavior: ["retry-once"],
      },
      {
        id: "contracts/example/complete-task-success",
        kind: "example",
        name: "complete-task-success",
        status: "accepted",
        demonstrates: ["contracts/workflow/complete-task"],
      },
    ],
  }).readinessReport();

  assert.deepEqual(
    report.diagnostics.map((diagnostic) => [diagnostic.code, diagnostic.objectId, diagnostic.path]),
    [
    ["ORIN-R030", "contracts/entity-type/task", "/objects/contracts~1entity-type~1task/lifecycle"],
    ["ORIN-R031", "contracts/effect/write-task", "/objects/contracts~1effect~1write-task/inputs"],
    ["ORIN-R032", "contracts/effect/write-task", "/objects/contracts~1effect~1write-task/outputs"],
    ["ORIN-R040", "contracts/rule/postcondition-proof", "/objects/contracts~1rule~1postcondition-proof/evidenceLinks"],
    ["ORIN-R050", "contracts/workflow/complete-task", "/objects/contracts~1workflow~1complete-task/postconditions"],
    ],
  );
  const ruleGap = report.diagnostics.find((diagnostic) => diagnostic.code === "ORIN-R040");
  assert.ok(ruleGap);
  assert.equal(ruleGap.message, "rule requires linked evidence contract");
  assert.deepEqual(ruleGap.affectedObjectPaths, [
    "/objects/contracts~1rule~1postcondition-proof",
    "/objects/contracts~1workflow~1complete-task",
    "/objects/contracts~1example~1complete-task-success",
  ]);
});

test("readiness extension fixtures are the cross-implementation parity source", async (t) => {
  const fixture = loadJson(READINESS_EXTENSION_CASES_FIXTURE);
  for (const readinessCase of fixture.cases || []) {
    await t.test(readinessCase.id, () => {
    const modelPath = resolve(ROOT, "tests/conformance", readinessCase.model);
    const report = new SemanticModel(loadJson(modelPath)).readinessReport();
    const requiredDecisionDiagnostics = report.diagnostics
      .filter((diagnostic) => diagnostic.category === "required-decision")
      .map((diagnostic) => ({
        code: diagnostic.code,
        category: diagnostic.category,
        blocking: diagnostic.blocking,
        objectId: diagnostic.objectId,
        path: diagnostic.path,
      }));
    assert.equal(report.status, readinessCase.then?.status);
    assert.equal(report.validationStatus, readinessCase.then?.validationStatus);
    assert.deepEqual(requiredDecisionDiagnostics, readinessCase.then?.requiredDecisionDiagnostics ?? []);
    });
  }
});
