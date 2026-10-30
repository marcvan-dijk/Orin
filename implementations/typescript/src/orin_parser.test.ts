import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { OrinParser, OrinSourceError, parseOrinFile } from "./orin_parser.ts";

const ROOT = resolve(fileURLToPath(new URL("../../..", import.meta.url)));

function strip(value: any): any {
  if (Array.isArray(value)) return value.map(strip);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).filter(([k]) => k !== "source").map(([k, v]) => [k, strip(v)]));
  }
  return value;
}

test("shared-tasks.minimal.orin matches JSON model plus open question", () => {
  const loaded = strip(parseOrinFile(resolve(ROOT, "examples/shared-tasks.minimal.orin")).document);
  const expected = strip(JSON.parse(readFileSync(resolve(ROOT, "tests/conformance/shared-tasks.minimal.model.json"), "utf-8")));
  const uncertainties = loaded.objects.filter((o: any) => o.kind === "uncertainty");
  assert.deepEqual(uncertainties.map((u: any) => u.name), ["non-member-completion"]);
  loaded.objects = loaded.objects.filter((o: any) => o.kind !== "uncertainty" && o.id !== "shared-tasks.minimal/evidence/blocked");
  const byId = (doc: any) => Object.fromEntries(doc.objects.map((o: any) => [o.id, o]));
  assert.deepEqual(loaded.module, expected.module);
  assert.deepEqual(byId(loaded), byId(expected));
});

test("source error conformance cases", () => {
  const cases = JSON.parse(readFileSync(resolve(ROOT, "tests/conformance/orin-source-errors.cases.json"), "utf-8")).cases;
  for (const c of cases) {
    assert.throws(
      () => new OrinParser().parse(c.source),
      (e: unknown) => e instanceof OrinSourceError && e.code === c.expectedDiagnostic && e.line === c.line && (c.column === undefined || e.column === c.column),
      c.id,
    );
  }
});

test("two blocking uncertainties and same-slug rules parse with distinct ids", () => {
  const text = "module: demo\n\npurpose:\n  Do a thing.\n\nrules:\n  - Things are done once only here.\n  - Things are done once only there.\n\n"
    + "uncertainty: first\n  blocking: yes\n  question:\n    One?\n\nuncertainty: second\n  blocking: yes\n  question:\n    Two?\n";
  const objects = new OrinParser().parseOutline(text).document.objects as any[];
  const ids = objects.map((o) => o.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.deepEqual(ids.filter((i) => i.includes("/rule/")), ["demo/rule/things-are-done-once-only", "demo/rule/things-are-done-once-only-2"]);
  assert.ok(ids.includes("demo/uncertainty/second"));
});

test("outline parameters become language-neutral module parameter declarations", () => {
  const model = new OrinParser().parseOutline(`module: bookings

parameter: capacity
  type: number
  unit: seats

rules:
  - An event never has more confirmed bookings than its capacity.
`);

  assert.deepEqual(model.document.module.parameters, [
    { name: "capacity", type: "number", unit: "seats" },
  ]);
  assert.deepEqual(
    model.document.objects.find((object: any) => object.kind === "rule").claims,
    ["An event never has more confirmed bookings than its capacity."],
  );
});
