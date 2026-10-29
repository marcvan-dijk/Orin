import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";

import { generate } from "./cli.ts";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const ROOT = resolve(HERE, "../../../..");
const conf = (name: string) => resolve(ROOT, "tests/conformance", name);
const text = (name: string) => readFileSync(conf(name), "utf-8");
const CLI = resolve(HERE, "cli.ts");
const SCRATCH = resolve(HERE, ".cli-scratch");

function runCli(...args: string[]) {
  return spawnSync(process.execPath, ["--experimental-strip-types", "--no-warnings", CLI, ...args], { encoding: "utf-8" });
}

test("cli generates password-reset into outdir", () => {
  rmSync(SCRATCH, { recursive: true, force: true });
  mkdirSync(SCRATCH, { recursive: true });
  try {
    writeFileSync(resolve(SCRATCH, "d.json"), JSON.stringify({ maxRequests: 2, windowSeconds: 60 }));
    const r = runCli(conf("password-reset.model.json"), resolve(SCRATCH, "d.json"), resolve(SCRATCH, "out"));
    assert.equal(r.status, 0, r.stderr);
    assert.match(readFileSync(resolve(SCRATCH, "out/password_reset.generated.ts"), "utf-8"), /maxRequests: 2/);
  } finally {
    rmSync(SCRATCH, { recursive: true, force: true });
  }
});

test("cli exit codes: usage, bad input, refusal", () => {
  rmSync(SCRATCH, { recursive: true, force: true });
  mkdirSync(SCRATCH, { recursive: true });
  try {
    const d = resolve(SCRATCH, "d.json");
    writeFileSync(d, JSON.stringify({ maxRequests: 0, windowSeconds: 1 }));
    assert.equal(runCli().status, 2);
    assert.equal(runCli("missing.json", d, SCRATCH).status, 2);
    const refused = runCli(conf("password-reset.model.json"), d, SCRATCH);
    assert.equal(refused.status, 1);
    assert.match(refused.stderr, /refused/);
    writeFileSync(d, "{nope");
    assert.equal(runCli(conf("password-reset.model.json"), d, SCRATCH).status, 2);
    writeFileSync(d, "{}");
    assert.equal(runCli(conf("shared-tasks.model.json"), d, SCRATCH).status, 2);
  } finally {
    rmSync(SCRATCH, { recursive: true, force: true });
  }
});

const decision = { noEligibleApprover: "stay-submitted" };

test("expense-approval: deterministic, accepts resolved copy, refuses bad decision", () => {
  const model = text("expense-approval.model.json");
  const a = generate(model, JSON.stringify(decision));
  assert.equal(a.source, generate(model, JSON.stringify(decision)).source);
  const copy = JSON.parse(model);
  copy.unresolved = [];
  assert.equal(generate(JSON.stringify(copy), JSON.stringify(decision)).source, a.source);
  assert.throws(() => generate(model, JSON.stringify({ noEligibleApprover: "x" })), /decision/);
});

test("generated expense module satisfies expense-approval conformance cases", async () => {
  const { source } = generate(text("expense-approval.model.json"), JSON.stringify(decision));
  mkdirSync(SCRATCH, { recursive: true });
  const file = resolve(SCRATCH, "expense.ts");
  writeFileSync(file, source);
  let gen: any;
  try {
    gen = await import(pathToFileURL(file).href);
  } finally {
    rmSync(SCRATCH, { recursive: true, force: true });
  }
  const cases = JSON.parse(text("expense-approval.cases.json")).cases.filter((c: any) => c.when.action !== "compile");
  assert.ok(cases.length > 0);
  for (const c of cases) {
    const g = c.given;
    const expense = new gen.Expense(g.amount, g.expense ?? "submitted");
    const approver = { limit: g.approverLimit, isSubmitter: g.approverIsSubmitter };
    const actual = c.when.action === "approve" ? expense.approve(approver) : expense.reject(approver, c.when.reason);
    for (const [key, value] of Object.entries(c.then)) assert.deepEqual(actual[key], value, `${c.id}: ${key}`);
  }
});
