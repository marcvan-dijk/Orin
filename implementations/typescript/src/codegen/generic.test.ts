import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";

import { generate } from "./cli.ts";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const ROOT = resolve(HERE, "../../../..");
const lending = readFileSync(resolve(ROOT, "tests/conformance/library-lending.decided.json"), "utf-8");
const SCRATCH = resolve(HERE, ".generic-scratch");

let counter = 0;
async function load(source: string) {
  rmSync(SCRATCH, { recursive: true, force: true });
  mkdirSync(SCRATCH, { recursive: true });
  const file = resolve(SCRATCH, `m${++counter}.ts`);
  writeFileSync(file, source);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(SCRATCH, { recursive: true, force: true });
  }
}

test("generic fallback generates library-lending deterministically", () => {
  const a = generate(lending, "{}");
  assert.equal(a.file, "library_lending_module.generated.ts");
  assert.equal(a.source, generate(lending, "{}").source);
});

test("rules throw NotImplementedRule until a hook exists; examples run as checks", async () => {
  const gen = await load(generate(lending, "{}").source);
  const fn = gen.rule_a_copy_is_on_loan;
  assert.throws(() => fn({}), gen.NotImplementedRule);
  assert.equal(fn({ "library-lending/rule/a-copy-is-on-loan": () => 7 }), 7);
  const id = "library-lending/example/on-time-loan";
  assert.throws(() => gen.checkExample(id, {}), gen.NotImplementedRule);
  assert.deepEqual(gen.checkExample(id, { [id]: () => true }), { example: "on-time-loan", passed: true });
  assert.throws(() => gen.runWorkflow("library-lending/workflow/borrow-book", null, {}), gen.NotImplementedRule);
});

test("workflow transitions become a state machine", async () => {
  const doc = JSON.parse(lending);
  doc.module.id = "x/module; evil";
  doc.objects.push({
    id: "library-lending/workflow/loan-cycle", kind: "workflow", name: "loan-cycle", status: "accepted",
    transitions: [{ from: "x/state/available", to: "x/state/on-loan" }],
  });
  const { source, file } = generate(JSON.stringify(doc), "{}");
  assert.match(file, /^x_module_evil\.generated\.ts$/);
  const gen = await load(source);
  const wf = "library-lending/workflow/loan-cycle";
  assert.deepEqual(gen.runWorkflow(wf, "available"), { ok: true, state: "on-loan" });
  assert.equal(gen.runWorkflow(wf, "on-loan").ok, false);
});

test("blocked model is refused", () => {
  const doc = JSON.parse(lending);
  doc.objects.find((o: any) => o.id.endsWith("lost-book-fee")).consequential = true;
  assert.throws(() => generate(JSON.stringify(doc), "{}"), /blocked|unresolved/);
});

function capacityModel(claims = ["An event never has more confirmed bookings than its capacity."]) {
  return {
    module: {
      id: "event-booking/module", kind: "module", name: "event-booking",
      parameters: [{ name: "capacity", type: "number", unit: "seats" }],
    },
    objects: [{ id: "event-booking/rule/capacity-limit", kind: "rule", claims }],
  };
}

test("capacity rule and helper enforce the declared parameter without hooks", async () => {
  const doc = capacityModel();
  const source = generate(JSON.stringify(doc), "{}").source;
  assert.equal(source, generate(JSON.stringify(doc), "{}").source);
  const gen = await load(source);
  const id = "event-booking/rule/capacity-limit";
  for (const [actual, capacity, expected] of [
    [0, 0, true], [0, 10, true], [9, 10, true], [10, 10, true], [11, 10, false],
    [1.5, 1.5, true], [1.6, 1.5, false],
  ]) {
    assert.equal(gen.withinCapacityLimit(id, actual, { capacity }), expected);
    assert.equal(gen.rule_capacity_limit(actual, { capacity }), expected);
    assert.equal(gen.RULE_FUNCTIONS[id](actual, { capacity }), expected);
  }
  for (const invalid of [-1, NaN, Infinity, -Infinity, "10", null, undefined, true]) {
    assert.throws(() => gen.rule_capacity_limit(invalid, { capacity: 10 }), RangeError);
    assert.throws(() => gen.rule_capacity_limit(1, { capacity: invalid }), RangeError);
  }
  for (const parameters of [{}, null, undefined, { other: 10 }, Object.create({ capacity: 10 })]) {
    assert.throws(() => gen.rule_capacity_limit(1, parameters), RangeError);
  }
  assert.throws(() => gen.withinCapacityLimit("unknown", 1, { capacity: 10 }), /unknown capacity rule/);
});

test("capacity derivation uses the claim's parameter, not a hardcoded capacity name", async () => {
  const doc = capacityModel(["An event never has more attendees than its seat-limit."]);
  doc.module.parameters[0].name = "seat-limit";
  const gen = await load(generate(JSON.stringify(doc), "{}").source);
  assert.equal(gen.rule_capacity_limit(2, { "seat-limit": 2 }), true);
  assert.equal(gen.rule_capacity_limit(3, { "seat-limit": 2 }), false);
  assert.throws(() => gen.rule_capacity_limit(1, { capacity: 2 }), RangeError);
});

test("additional or unrecognized claims remain hook-based", async () => {
  for (const claims of [
    ["An event never has more confirmed bookings than its capacity.", "Bookings require approval."],
    ["Bookings require approval."],
    ["An event never has more confirmed bookings than its capacity is over."],
  ]) {
    const gen = await load(generate(JSON.stringify(capacityModel(claims)), "{}").source);
    assert.throws(() => gen.rule_capacity_limit({}), gen.NotImplementedRule);
    assert.equal(gen.rule_capacity_limit({ "event-booking/rule/capacity-limit": () => 7 }), 7);
  }
});

test("invalid module parameters refuse generation even when unused", () => {
  const doc = capacityModel(["Bookings require approval."]);
  doc.module.parameters[0].unit = "";
  assert.throws(() => generate(JSON.stringify(doc), "{}"), /fail/);
});
