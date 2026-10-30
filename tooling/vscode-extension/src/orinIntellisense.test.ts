import * as assert from "node:assert";
import { completionsAt, findDeclarations, findDefinition, findReferences, idAt, SNIPPETS } from "./orinIntellisense";

const doc = [
  "module: m.x",
  "",
  "capability: person.reset",
  "",
  "rule: token-expiry",
  "  claims:",
  "    - Tokens expire.",
  "",
  "workflow: request",
  "  requires:",
  "    person.reset",
  "  claims:",
  "    - See token-expiry.",
  "",
  "example: ok",
  "  given:",
  "    x",
  "",
].join("\n");

assert.deepStrictEqual(findDeclarations(doc).map((d) => d.id), ["m.x", "person.reset", "token-expiry", "request", "ok"]);
assert.deepStrictEqual(findDefinition(doc, { line: 10, character: 6 }), { line: 2, start: 12, end: 24 });
assert.strictEqual(findDefinition(doc, { line: 10, character: 0 }), undefined);
assert.strictEqual(findDefinition(doc, { line: 6, character: 6 }), undefined);
assert.deepStrictEqual(findReferences(doc, { line: 4, character: 8 }).map((s) => s.line), [4, 12]);
assert.deepStrictEqual(findReferences(doc, { line: 4, character: 8 }, false).map((s) => s.line), [12]);
assert.deepStrictEqual(findReferences(doc, { line: 10, character: 6 }).map((s) => s.line), [2, 10]);
assert.strictEqual(idAt(doc, { line: 12, character: 15 }) !== undefined, true);
assert.deepStrictEqual(findReferences("rule: ab\n  x abc ab-c ab\n", { line: 0, character: 7 }).map((s) => s.line), [0, 1]);

const top = completionsAt("ru", { line: 0, character: 2 }).map((c) => c.label);
assert.deepStrictEqual(top, ["rule:"]);
assert.ok(completionsAt("rule: a\n  ", { line: 1, character: 2 }).some((c) => c.label === "claims:"));
assert.ok(completionsAt("uncertainty: u\n  op", { line: 1, character: 4 }).some((c) => c.label === "option:"));
assert.ok(["given:", "when:", "then:"].every((k) => completionsAt("example: e\n  ", { line: 1, character: 2 }).some((c) => c.label === k)));
const withTok = doc + "  requires: tok";
const ids = completionsAt(withTok, { line: withTok.split("\n").length - 1, character: 16 });
assert.deepStrictEqual(ids.map((c) => c.label), ["token-expiry"]);
assert.deepStrictEqual(completionsAt("rule: to", { line: 0, character: 8 }), []);
assert.deepStrictEqual(SNIPPETS.map((s) => s.prefix), ["rule", "uncertainty", "example"]);
console.log("orinIntellisense tests passed");
