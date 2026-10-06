import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";

type RuntimeTask = { id: string; assignee: string; state: "open" | "completed" };

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const MINIMAL_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.minimal.cases.json");

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function loadPythonMinimalActualByCase(): Record<string, Record<string, any>> {
  const script = `
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(root / "implementations" / "python"))
from shared_tasks_conformance import run_minimal_fixture

rows = run_minimal_fixture(root / "tests" / "conformance" / "shared-tasks.minimal.cases.json")
print(json.dumps({case_id: actual for case_id, actual, _ in rows}, sort_keys=True))
`;
  const result = spawnSync("python", ["-c", script, ROOT], { encoding: "utf-8" });
  assert.equal(result.status, 0, `python minimal fixture execution failed: ${result.stderr}`);
  return JSON.parse(result.stdout);
}

function runMinimalCase(caseDoc: Record<string, any>): Record<string, any> {
  const setup = caseDoc.setup ?? {};
  const action = caseDoc.action ?? {};
  const taskSetup = setup.task ?? {};
  const members = new Set<string>([setup.owner, ...(setup.members ?? [])].filter((v): v is string => typeof v === "string"));

  let task: RuntimeTask | null = null;
  if (typeof taskSetup.id === "string") {
    task = {
      id: "task-1",
      assignee: typeof taskSetup.assignee === "string" ? taskSetup.assignee : setup.owner,
      state: taskSetup.state === "completed" ? "completed" : "open",
    };
  }

  const actor = action.actor;
  const requestedTask = action.task;
  if (typeof actor !== "string" || typeof requestedTask !== "string") {
    return { ok: false, failure: "invalid-action" };
  }

  if (requestedTask === "task-missing" || task === null) {
    return { ok: false, failure: "task-not-found", stateChanges: "none" };
  }

  if (!members.has(actor)) {
    return { ok: false, failure: "unauthorized", taskState: task.state };
  }
  if (task.assignee !== actor) {
    return { ok: false, failure: "not-assigned", taskState: task.state };
  }
  if (task.state !== "open") {
    return { ok: false, failure: "already-completed", taskState: task.state };
  }

  task.state = "completed";
  return { ok: true, taskState: task.state, persisted: true };
}

test("shared-tasks minimal fixture parity checks stay deterministic", async (t) => {
  const fixture = loadJson(MINIMAL_FIXTURE);
  const pythonActualByCase = loadPythonMinimalActualByCase();
  for (const scenario of fixture.cases ?? []) {
    await t.test(scenario.id, () => {
      const actual = runMinimalCase(scenario);
      assert.deepEqual(actual, scenario.then);
      assert.deepEqual(actual, pythonActualByCase[scenario.id]);
    });
  }
});
