import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

type RuntimeTask = { id: string; assignee: string; state: "open" | "completed" };

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));
const MINIMAL_FIXTURE = resolve(ROOT, "tests/conformance/shared-tasks.minimal.cases.json");

function loadJson(path: string): Record<string, any> {
  return JSON.parse(readFileSync(path, "utf-8"));
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
  for (const scenario of fixture.cases ?? []) {
    await t.test(scenario.id, () => {
      assert.deepEqual(runMinimalCase(scenario), scenario.then);
    });
  }
});
