import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

import { SemanticModel } from "./orin_model.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const RULE_CONTRADICTION_MULTI_FIXTURE = resolve(
  ROOT,
  "tests/conformance/shared-tasks.rule-contradiction-multi.model.json",
);

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
}

test("rule multi-contradiction diagnostic entries are deterministic", () => {
  const model = new SemanticModel(loadJson(RULE_CONTRADICTION_MULTI_FIXTURE));
  const contradictionEntries = model
    .diagnostics()
    .filter((diagnostic) => diagnostic.code === "ORIN-E046")
    .map((diagnostic) => ({
      code: diagnostic.code,
      objectId: diagnostic.objectId,
      message: diagnostic.message,
    }));

  assert.deepEqual(contradictionEntries, [
    {
      code: "ORIN-E046",
      objectId: "shared-tasks/rule/member-completion",
      message: "rule contains contradictory claims: assignee must be a list member",
    },
    {
      code: "ORIN-E046",
      objectId: "shared-tasks/rule/member-completion",
      message: "rule contains contradictory claims: task title must be non-empty",
    },
  ]);
  assert.equal(model.compilationStatus(), "fail");
});
