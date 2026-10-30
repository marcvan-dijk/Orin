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
