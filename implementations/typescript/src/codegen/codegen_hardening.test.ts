import test from "node:test";
import assert from "node:assert/strict";
import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import { resolve } from "node:path";

import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, generatePasswordReset } from "./generate_password_reset.ts";
import { generateExpenseApproval } from "./generate_expense_approval.ts";

const ROOT = resolve(fileURLToPath(new URL("../../../..", import.meta.url)));
const load = (name: string) => JSON.parse(readFileSync(resolve(ROOT, "tests/conformance", name), "utf-8"));
const prDecision = { maxRequests: 3, windowSeconds: 600 };
const exDecision = { noEligibleApprover: "stay-submitted" } as const;

const HOSTILE = [
  "a\nglobalThis.INJECTED = 1;\n// ",
  "*/ globalThis.INJECTED = 1; /*",
  "`${globalThis.INJECTED = 1}`",
  "'\"\\ \\u{0} \\x00",
  "\u2028globalThis.INJECTED = 1;\u2029",
  "\r\n\u0085\u000b\u000c ünï©ödé 日本語 😀",
  "x".repeat(100_000),
  "",
];

const KEEP = new Set(["id", "claims", "kind", "status", "from", "to", "target", "source", "uses", "capability",
  "state", "states", "type", "default", "unresolved", "decision", "options"]);
function poison(value: any, text: string, key = ""): any {
  if (Array.isArray(value)) return value.map((v) => poison(v, text, key));
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([k, v]) => [k, KEEP.has(k) ? v : poison(v, text, k)]));
  }
  return typeof value === "string" && !KEEP.has(key) ? text : value;
}

const generators = [
  { name: "password-reset", model: "password-reset.model.json", gen: (m: SemanticModel) => generatePasswordReset(m, prDecision) },
  { name: "expense-approval", model: "expense-approval.model.json", gen: (m: SemanticModel) => generateExpenseApproval(m, exDecision) },
];

let seq = 0;
async function importSource(source: string) {
  const dir = resolve(fileURLToPath(new URL(".", import.meta.url)), ".generated_hardening");
  mkdirSync(dir, { recursive: true });
  const file = resolve(dir, `gen_${++seq}.ts`);
  writeFileSync(file, source);
  try {
    return await import(pathToFileURL(file).href);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

for (const g of generators) {
  test(`${g.name}: hostile model text never injects, compiles, and is deterministic`, async () => {
    delete (globalThis as any).INJECTED;
    for (const text of HOSTILE) {
      for (const hostileId of [false, true]) {
        const doc = poison(load(g.model), text);
        if (hostileId) { if (!text) continue; doc.module.id = text; }
        const model = new SemanticModel(doc);
        const source = g.gen(model);
        assert.equal(source, g.gen(new SemanticModel(doc)));
        const header = source.split("\n").slice(0, 2).join("\n");
        assert.doesNotMatch(header, /[\u2028\u2029\r\u0085]/);
        assert.ok(source.split("\n").slice(0, 2).every((l) => l.startsWith("//")), "header stays in comments");
        assert.ok(source.length < 50_000);
        await importSource(source);
        assert.equal((globalThis as any).INJECTED, undefined);
      }
    }
  });

  test(`${g.name}: malformed models are refused with GenerationRefused`, () => {
    const base = load(g.model);
    const bad: any[] = [{}, { ...base, objects: "nope" }, { ...base, module: "nope" }, { ...base, unresolved: 5 },
      { ...base, objects: [null, 1, "x"] }];
    for (const doc of bad) {
      assert.throws(() => g.gen(new SemanticModel(doc)), (e: unknown) => {
        return e instanceof GenerationRefused && !/^\s+at /m.test(e.message);
      }, JSON.stringify(doc).slice(0, 60));
    }
  });
}

test("malformed decisions are refused", () => {
  const m = new SemanticModel(load("password-reset.model.json"));
  for (const d of [null, undefined, {}, { maxRequests: 0, windowSeconds: 1 }, { maxRequests: 1.5, windowSeconds: 1 },
    { maxRequests: NaN, windowSeconds: 1 }, { maxRequests: "1; evil()", windowSeconds: 1 }] as any[]) {
    assert.throws(() => generatePasswordReset(m, d), GenerationRefused);
  }
  const e = new SemanticModel(load("expense-approval.model.json"));
  for (const d of [null, {}, { noEligibleApprover: '"; evil(); "' }] as any[]) {
    assert.throws(() => generateExpenseApproval(e, d), GenerationRefused);
  }
});
