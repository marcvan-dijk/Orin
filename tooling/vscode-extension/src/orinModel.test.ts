import * as assert from "node:assert";
import * as fs from "node:fs";
import * as path from "node:path";
import { parseOutline, workflowHover, findWorkflowAt, parseAgentOutput, parseDecisions, findUncertaintyLine, defaultResolvedPath, buildDecideArgs, decideSucceeded } from "./orinModel";

const src = fs.readFileSync(path.resolve(__dirname, "..", "..", "..", "examples", "password-reset.orin"), "utf8");
const outline = parseOutline(src);
const kinds = outline.symbols.map((s) => s.kind);
const srcLines = src.split(/\r?\n/);
for (const kind of ["rule", "workflow", "example", "capability", "state", "type", "uncertainty"]) {
  const declared = srcLines.filter((l) => l.startsWith(`${kind}:`)).length;
  assert.ok(declared > 0, `fixture has ${kind}`);
  assert.strictEqual(kinds.filter((k) => k === kind).length, declared, `${kind} count`);
}
const optOutline = parseOutline("uncertainty: u\n  option: a\n    label: A\n  option: b\n");
assert.deepStrictEqual(optOutline.symbols.map((x) => x.kind), ["uncertainty", "option", "option"]);
const wf = outline.symbols.find((s) => s.kind === "workflow")!;
assert.ok(findWorkflowAt(outline, wf.startLine + 2));
assert.ok(workflowHover(outline, wf).includes(outline.modulePurpose!));
const o = parseOutline("workflow: a\n  actor: Admin\n  purpose:\n    Do it\n  steps:\n    x\n");
assert.strictEqual(o.symbols[0].actor, "Admin");
assert.strictEqual(o.symbols[0].purpose, "Do it");
const s = parseAgentOutput("Compilation: blocked\nValidation: blocked\n\n1. a/b\n   Question: Why?\n");
assert.deepStrictEqual(s, { status: "blocked", decisions: ["a/b: Why?"] });
assert.strictEqual(parseAgentOutput("Compilation: ready\nValidation: ready").status, "ready");
const d = parseDecisions("1. a/uncertainty/rate-limit\n   Question: Why?\n   Options:\n   - x: Do x.\n     Why choose it: Because.\n     Compilation: blocked\n   - defer: Later.\n");
assert.strictEqual(d[0].options.length, 2);
assert.deepStrictEqual(d[0].options[0], { id: "x", description: "Do x.", whyChoose: "Because.", compilation: "blocked" });
assert.strictEqual(findUncertaintyLine(src, "account.password-reset/uncertainty/rate-limit"), srcLines.indexOf("uncertainty: rate-limit"));
assert.strictEqual(defaultResolvedPath("/a/b/x.orin"), "/a/b/x.resolved.json");
assert.strictEqual(defaultResolvedPath("C:\\a\\x.model.json"), "C:\\a\\x.model.resolved.json");
assert.deepStrictEqual(buildDecideArgs("f.orin", "u", "o", "w.json").slice(3), ["f.orin", "--uncertainty", "u", "--option", "o", "--write", "w.json"]);
assert.ok(decideSucceeded(4) && !decideSucceeded(3) && !decideSucceeded(0) && !decideSucceeded(undefined));

const root = path.resolve(__dirname, "..", "..", "..");
const files = ["examples", path.join("examples", "authoring")].flatMap((dir) =>
  fs.readdirSync(path.join(root, dir)).filter((f) => f.endsWith(".orin")).map((f) => path.join(root, dir, f)),
);
assert.ok(files.length >= 8);
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const lines = text.split(/\r?\n/);
  const ol = parseOutline(text);
  const label = path.basename(file);
  assert.ok(ol.symbols.length > 0, `${label}: empty outline`);
  assert.ok(ol.modulePurpose, `${label}: missing module purpose`);
  for (const sym of ol.symbols) {
    assert.ok(sym.startLine <= sym.endLine && sym.endLine < lines.length, `${label}: bad range ${sym.name}`);
  }
  const declared = lines.filter((l) => /^\s*workflow\b/.test(l)).length;
  const workflows = ol.symbols.filter((x) => x.kind === "workflow");
  assert.strictEqual(workflows.length, declared, `${label}: workflow count`);
  for (const w of workflows) {
    assert.ok(findWorkflowAt(ol, w.startLine), `${label}: no workflow at start`);
    const hover = workflowHover(ol, w);
    assert.ok(hover.includes(w.name) && hover.includes("Purpose"), `${label}: hover ${w.name}`);
  }
  const uncertainties = lines.filter((l) => /^\s*uncertainty\b/.test(l)).length;
  assert.strictEqual(ol.symbols.filter((x) => x.kind === "uncertainty").length, uncertainties, `${label}: uncertainties`);
  for (const sym of ol.symbols.filter((x) => x.kind === "uncertainty")) {
    assert.strictEqual(lines[findUncertaintyLine(text, sym.name)].includes(sym.name), true, `${label}: uncertainty line`);
  }
}
const brace = parseOutline(fs.readFileSync(path.join(root, "examples", "authoring", "book-lending.orin"), "utf8"));
assert.strictEqual(brace.symbols.filter((x) => x.kind === "rule").length, 3);
assert.strictEqual(brace.symbols.filter((x) => x.kind === "example").length, 2);
assert.strictEqual(brace.symbols.filter((x) => x.kind === "uncertainty").length, 2);
const lend = brace.symbols.find((x) => x.kind === "workflow")!;
assert.ok(lend.endLine > lend.startLine);
console.log("orinModel tests passed");
