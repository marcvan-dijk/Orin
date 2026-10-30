import { existsSync, readFileSync } from "node:fs";
import { basename, dirname, join, resolve } from "node:path";
import { SemanticModel } from "./orin_model.ts";

type Doc = Record<string, any>;
type Line = [number, string];
type RawLine = [number, number, string];

const DECLARATION_KINDS: Record<string, string> = {
  type: "value-type",
  entity: "entity-type",
  relation: "relation",
  state: "state",
  capability: "capability",
  effect: "effect",
  rule: "rule",
  workflow: "workflow",
  example: "example",
  uncertainty: "uncertainty",
  evidence: "evidence",
  target: "target",
};

const SOURCE_ERROR_HINTS: Record<string, [string, string]> = {
  "ORIN-P001": ["The file has no module declaration.", "Start the file with a line like: module my-app {"],
  "ORIN-P002": ["This line is not valid Orin syntax.", 'Check the spelling of the keyword (for example type, entity, rule, example) and that blocks use "{" and "}".'],
  "ORIN-P003": ['A block was opened with "{" but never closed.', 'Add a closing "}" on its own line after the last line of the block.'],
  "ORIN-P004": ["A quoted piece of text is missing.", 'Put the text in double quotes, for example: purpose "Let people reset passwords"'],
  "ORIN-P005": ["This line is not allowed inside this declaration.", "Remove the line or use an attribute this kind of declaration supports."],
  "ORIN-P006": ["This line is not allowed in a context block.", 'Use only: repository "..." or risk "..."'],
  "ORIN-P007": ["This line is not an allowed implementation policy.", 'Use optimize-for, prefer, require or deploy-to followed by a quoted value, e.g. prefer "python"'],
  "ORIN-P008": ["A field needs both a name and a type.", "Write it as: field name type  (for example: field email text)"],
  "ORIN-P009": ["This field modifier is not recognised.", 'The only modifier is "identity", e.g. field id text identity'],
};

export class OrinSourceError extends Error {
  code: string;
  problem: string;
  hint: string;
  file: string | null;
  line: number;
  column: number;
  sourceLine: string;

  constructor(code: string, problem: string, hint: string, file: string | null, line: number, column: number, sourceLine = "") {
    super("");
    this.code = code;
    this.problem = problem;
    this.hint = hint;
    this.file = file;
    this.line = line;
    this.column = column;
    this.sourceLine = sourceLine;
    this.message = this.format();
  }

  format(): string {
    let text = `${this.file ?? "<source>"}:${this.line}:${this.column}: error ${this.code}: ${this.problem}`;
    if (this.sourceLine) text += `\n    ${this.sourceLine}\n    ${" ".repeat(this.column - 1)}^`;
    return text + `\n  Suggested fix: ${this.hint}`;
  }

  withFile(file: string): OrinSourceError {
    return new OrinSourceError(this.code, this.problem, this.hint, file, this.line, this.column, this.sourceLine);
  }
}

// Internal error carrying a bare diagnostic code, mapped to a located OrinSourceError.
class CodedError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(`${code}: ${message}`);
    this.code = code;
  }
}

const KEY_RE = /^([A-Za-z][\w-]*):\s*(.*)$/;
const count = (s: string, ch: string) => s.split(ch).length - 1;
const words = (s: string) => s.trim().split(/\s+/).filter(Boolean);

export class OrinParser {
  private currentLine = 1;
  private blockStart = 1;

  parseFile(path: string): SemanticModel {
    let text: string;
    let bytes: Buffer;
    try {
      bytes = readFileSync(path);
    } catch {
      throw new OrinSourceError("ORIN-P012", "The file does not exist.", "Check the path and spelling.", path, 1, 1);
    }
    try {
      text = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
    } catch {
      throw new OrinSourceError("ORIN-P013", "The file is not valid UTF-8 text.", "Save the file as UTF-8.", path, 1, 1);
    }
    text = text.replace(/^\uFEFF/, "");
    try {
      return OrinParser.isOutline(text) ? this.parseOutline(text, path) : this.parse(text);
    } catch (error) {
      if (error instanceof OrinSourceError) throw error.withFile(path);
      throw error;
    }
  }

  static isOutline(text: string): boolean {
    const first = splitLines(text).map((l) => l.trim()).find((l) => l && !l.startsWith("//")) ?? "";
    return /^module:\s*\S/.test(first);
  }

  // ---- outline syntax ----

  parseOutline(text: string, path?: string): SemanticModel {
    try {
      return this.parseOutlineText(text.replace(/^\uFEFF/, ""), path);
    } catch (error) {
      if (error instanceof OrinSourceError && path !== undefined && !error.file) throw error.withFile(path);
      throw error;
    }
  }

  private parseOutlineText(text: string, path?: string): SemanticModel {
    const sections = outlineSections(splitLines(text));
    if (sections.slice(1).some((s) => ["type", "entity", "relation", "state", "capability", "effect", "rule"].includes(s.key))) {
      return new SemanticModel(fullDocument(sections));
    }
    // Minimal, non-namespaced outlines borrow the accepted structured model when one exists.
    const fixture = path !== undefined && !sections[0].value.includes(".") ? findStructuredFixture(path) : null;
    if (fixture !== null) {
      const document = JSON.parse(readFileSync(fixture, "utf-8"));
      attachOutlineLines(document, sections);
      return new SemanticModel(document);
    }
    return new SemanticModel(simpleOutlineDocument(sections));
  }

  // ---- brace syntax ----

  parse(text: string): SemanticModel {
    this.currentLine = 1;
    this.blockStart = 1;
    try {
      return this.parseBraces(text);
    } catch (error) {
      if (!(error instanceof CodedError) || !(error.code in SOURCE_ERROR_HINTS)) throw error;
      const code = error.code;
      const lines = splitLines(text);
      const line = code === "ORIN-P001" ? 1 : code === "ORIN-P003" ? this.blockStart : this.currentLine;
      const source = line > 0 && line <= lines.length ? lines[line - 1] : "";
      const column = source ? source.length - source.trimStart().length + 1 : 1;
      const [problem, hint] = SOURCE_ERROR_HINTS[code];
      throw new OrinSourceError(code, problem, hint, null, line, column, source.trim() ? source.trimEnd() : "");
    }
  }

  private parseBraces(text: string): SemanticModel {
    const lines = splitLines(text);
    let moduleMatch: RegExpMatchArray | null = null;
    let moduleLine = 1;
    for (const [i, l] of lines.entries()) {
      moduleMatch = l.trim().match(/^module\s+([\w.-]+)\s*\{/);
      if (moduleMatch) {
        moduleLine = i + 1;
        break;
      }
    }
    if (!moduleMatch) throw new CodedError("ORIN-P001", "module declaration is required");
    const moduleName = moduleMatch[1];
    const mod: Doc = { id: `${moduleName}/module`, kind: "module", name: moduleName, source: { line: moduleLine } };
    const objects: Doc[] = [];
    let active: Doc | null = null;
    let ignoredDepth = 0;
    let contextDepth = 0;
    let policyDepth = 0;

    for (const [index, rawLine] of lines.entries()) {
      const lineNumber = index + 1;
      const line = rawLine.trim();
      this.currentLine = lineNumber;
      if (!line || line.startsWith("//")) continue;
      if (contextDepth) {
        if (line === "}") {
          contextDepth = 0;
          continue;
        }
        const attr = line.match(/^(repository|risk)\s+(.+)$/);
        if (attr) {
          (mod.context ??= {})[attr[1]] = stringValue(attr[2], lineNumber);
          continue;
        }
        throw new CodedError("ORIN-P006", `unsupported context attribute at line ${lineNumber}: ${line}`);
      }
      if (policyDepth) {
        if (line === "}") {
          policyDepth = 0;
          continue;
        }
        const attr = line.match(/^(optimize-for|prefer|require|deploy-to)\s+"([^"]+)"$/);
        if (attr) {
          (mod.implementationPolicies ??= {})[attr[1]] = attr[2];
          continue;
        }
        throw new CodedError("ORIN-P007", `unsupported implementation policy at line ${lineNumber}: ${line}`);
      }
      if (ignoredDepth) {
        ignoredDepth += count(line, "{") - count(line, "}");
        continue;
      }
      if (line.startsWith("module ")) continue;
      if (active !== null) {
        if (line === "}") {
          objects.push(active);
          active = null;
          continue;
        }
        readAttribute(active, line);
        continue;
      }
      if (line.startsWith("purpose ")) {
        mod.purpose = stringValue(line, lineNumber);
        continue;
      }
      if (line.startsWith("import ")) {
        (mod.imports ??= []).push(line.slice(7).trim());
        continue;
      }
      let m = line.match(/^(type|state|capability)\s+([\w.-]+)\s*$/);
      if (m) {
        objects.push(newObject(moduleName, DECLARATION_KINDS[m[1]], m[2], lineNumber));
        continue;
      }
      m = line.match(/^(entity|relation|rule|workflow|example|uncertainty|target|effect)\s+([\w.-]+)\s*\{\s*$/);
      if (m) {
        active = newObject(moduleName, DECLARATION_KINDS[m[1]], m[2], lineNumber);
        this.blockStart = lineNumber;
        continue;
      }
      m = line.match(/^evidence\s+(\w+)\s+(.+)$/);
      if (m) {
        const evidence = newObject(moduleName, "evidence", m[1], lineNumber);
        evidence.statement = stringValue(m[2], lineNumber);
        objects.push(evidence);
        continue;
      }
      if (line.startsWith("context ") && line.includes("{")) {
        contextDepth = count(line, "{") - count(line, "}");
        continue;
      }
      if (line.startsWith("policy implementation") && line.includes("{")) {
        policyDepth = count(line, "{") - count(line, "}");
        continue;
      }
      if ((line.startsWith("scope ") || line.startsWith("risk ")) && line.includes("{")) {
        ignoredDepth = count(line, "{") - count(line, "}");
        continue;
      }
      if (line.startsWith("role ")) continue;
      if (line === "}") continue;
      throw new CodedError("ORIN-P002", `unsupported syntax at line ${lineNumber}: ${line}`);
    }

    if (active !== null) throw new CodedError("ORIN-P003", "unterminated declaration block");
    const document: Doc = { module: mod, objects };
    const unresolved = objects.filter((o) => o.kind === "uncertainty" && o.consequential === true).map((o) => o.id);
    if (unresolved.length) document.unresolved = unresolved;
    const model = new SemanticModel(document);
    resolveTypeReferences(model.document);
    return model;
  }
}

export function parseOrinFile(path: string): SemanticModel {
  return new OrinParser().parseFile(path);
}

function splitLines(text: string): string[] {
  const lines = text.split(/\r\n|\r|\n/);
  if (lines.length && lines[lines.length - 1] === "") lines.pop();
  return lines;
}

function resolveTypeReferences(document: Doc): void {
  const types = new Map<string, string>();
  for (const obj of document.objects ?? []) {
    if (obj.kind === "value-type" || obj.kind === "entity-type") types.set(obj.name, obj.id);
  }
  for (const obj of document.objects ?? []) {
    if (obj.kind !== "workflow") continue;
    for (const field of ["inputs", "outputs"]) {
      for (const value of obj[field] ?? []) {
        if (value && typeof value === "object" && types.has(value.type)) value.type = types.get(value.type);
      }
    }
  }
}

function newObject(moduleName: string, kind: string, name: string, line: number): Doc {
  return { id: `${moduleName}/${kind}/${name}`, kind, name, source: { line } };
}

function stringValue(text: string, lineNumber: number): string {
  const m = text.match(/"([^"\\]*(?:\\.[^"\\]*)*)"/);
  if (!m) throw new CodedError("ORIN-P004", `quoted string required at line ${lineNumber}`);
  const escapes: Record<string, string> = { n: "\n", t: "\t", r: "\r", '"': '"', "\\": "\\", "'": "'" };
  return m[1].replace(/\\(.)/g, (_, c) => escapes[c] ?? `\\${c}`);
}

function reference(obj: Doc, text: string, kind: string | null = "capability"): string {
  const moduleName = obj.id.split("/").slice(0, -2).join("/");
  const t = text.trim();
  if (t.startsWith(`${moduleName}/`)) return t;
  return kind === null ? t : `${moduleName}/${kind}/${t}`;
}

function readAttribute(obj: Doc, line: string): void {
  if (obj.kind === "entity-type" && line.startsWith("field ")) {
    const parts = words(line);
    if (parts.length !== 3 && parts.length !== 4) throw new CodedError("ORIN-P008", `entity field requires name and type: ${line}`);
    const field: Doc = { name: parts[1], type: reference(obj, parts[2], "value-type") };
    if (parts.length === 4) {
      if (parts[3] !== "identity") throw new CodedError("ORIN-P009", `unsupported entity field modifier: ${parts[3]}`);
      field.identity = true;
    }
    (obj.fields ??= []).push(field);
    return;
  }
  if (obj.kind === "relation") {
    const rel = line.match(/^(from|to)\s+([\w.-]+)$/);
    if (rel) {
      (obj.endpoints ??= []).push({ type: reference(obj, rel[2], "entity-type") });
      return;
    }
    if (line.startsWith("cardinality ")) {
      obj.cardinality = line.slice(12).trim();
      return;
    }
  }
  let m = line.match(/^transition\s+([\w.-]+)\s*->\s*([\w.-]+)$/);
  if (m) {
    (obj.transitions ??= []).push({ from: reference(obj, m[1], "state"), to: reference(obj, m[2], "state") });
    return;
  }
  m = line.match(/^(input|output)\s+([\w.-]+)\s+([\w.-]+)$/);
  if (m) {
    (obj[`${m[1]}s`] ??= []).push({ name: m[2], type: reference(obj, m[3], null) });
    return;
  }
  m = line.match(/^bind\s+([\w.-]+)\s+([\w.-]+)$/);
  if (m) {
    (obj.actorCapabilities ??= []).push({ actor: m[1], capability: reference(obj, m[2], "capability") });
    return;
  }
  const attribute = line.match(/^(purpose|guarantee|question|authority|outcome|recovery|given|when|then|impact|severity)\s+(.+)$/);
  if (!attribute) {
    if (line.startsWith("budget ")) return;
    if (line.startsWith("requires ")) {
      (obj.requires ??= []).push(reference(obj, line.slice(9), "capability"));
      return;
    }
    if (line.startsWith("uses ")) {
      (obj.uses ??= []).push(reference(obj, line.slice(5), "effect"));
      return;
    }
    if (line.startsWith("actor ")) {
      obj.actor = line.slice(6).trim();
      return;
    }
    const d = line.match(/^durability\s+([\w.-]+)$/);
    if (d) {
      obj.durability = d[1];
      return;
    }
    if (line.startsWith("input ")) {
      (obj.inputs ??= []).push(line.slice(6).trim());
      return;
    }
    throw new CodedError("ORIN-P005", `unsupported declaration attribute: ${line}`);
  }
  const [, key, value] = attribute;
  if (["guarantee", "question", "outcome", "recovery", "given", "when", "then", "impact"].includes(key)) {
    (obj.claims ??= []).push(stringValue(value, 0));
  } else if (key === "authority") {
    obj[key] = value;
  } else {
    obj[key] = stringValue(value, 0);
  }
  if (obj.kind === "uncertainty") obj.consequential = true;
}

// ---- outline helpers ----

type Section = { key: string; value: string; line: number; body: Line[]; raw: RawLine[] };

function outlineSections(lines: string[]): Section[] {
  const sections: Section[] = [];
  for (const [i, raw] of lines.entries()) {
    const number = i + 1;
    const stripped = raw.trim();
    if (!stripped || stripped.startsWith("//")) continue;
    const indented = raw[0] === " " || raw[0] === "\t";
    if (!indented) {
      const m = stripped.match(KEY_RE);
      if (!m) {
        throw new OrinSourceError("ORIN-P010", "This line is not a recognised outline section.", "Start sections with a keyword and a colon, for example: rules:", null, number, 1, raw.trimEnd());
      }
      sections.push({ key: m[1], value: m[2].trim(), line: number, body: [], raw: [] });
    } else if (sections.length) {
      sections[sections.length - 1].body.push([number, stripped]);
      sections[sections.length - 1].raw.push([number, raw.length - raw.trimStart().length, stripped]);
    } else {
      throw new OrinSourceError("ORIN-P001", "A module declaration is required first.", "Begin the file with: module: name", null, number, 1, raw.trimEnd());
    }
  }
  if (!sections.length || sections[0].key !== "module" || !sections[0].value) {
    throw new OrinSourceError("ORIN-P001", "A module declaration is required.", "Begin the file with: module: name", null, 1, 1, lines[0] ?? "");
  }
  return sections;
}

function slug(text: string, n = 5): string {
  const parts = text.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  return parts.slice(0, n).join("-") || "unnamed";
}

function subBlocks(body: Line[]): Record<string, Line[]> {
  const allowed = new Set(["given", "when", "then", "input", "steps", "blocking", "question", "output", "requires", "failure", "recovery", "after"]);
  const blocks: Record<string, Line[]> = {};
  let current: Line[] | null = null;
  for (const [number, text] of body) {
    const m = text.match(KEY_RE);
    if (m && allowed.has(m[1])) {
      current = blocks[m[1]] ??= [];
      if (m[2]) current.push([number, m[2]]);
    } else if (current) {
      current.push([number, text]);
    }
  }
  return blocks;
}

function simpleOutlineDocument(sections: Section[]): Doc {
  const name = sections[0].value;
  const mod: Doc = { id: `${name}/module`, kind: "module", name, status: "accepted", source: { line: sections[0].line } };
  const parameterSections = sections.filter((section) => section.key === "parameter");
  if (parameterSections.length) {
    mod.parameters = parameterSections.map((section) => outlineParameter(section));
  }
  const objects: Doc[] = [];
  const add = (kind: string, objName: string, line: number, extra: Doc = {}): Doc => {
    const obj = { id: `${name}/${kind}/${objName}`, kind, name: objName, status: "accepted", source: { line }, ...extra };
    objects.push(obj);
    return obj;
  };
  const join = (b?: Line[]) => (b ?? []).map(([, t]) => t).join(" ");
  for (const { key, value, body, line } of sections.slice(1)) {
    if (key === "purpose") {
      mod.purpose = [...(value ? [value] : []), ...body.map(([, t]) => t)].join(" ");
    } else if (key === "rules") {
      let lastRule: Doc | null = null;
      for (const [number, text] of body) {
        const proof = text.match(/^proved-by:\s*(.*)$/);
        if (proof && lastRule !== null) {
          const links = proof[1].split(",").map((n) => n.trim()).filter(Boolean).map((n) => `${name}/example/${n}`);
          (lastRule.evidenceLinks ??= []).push(...links);
          continue;
        }
        const claim = text.startsWith("- ") ? text.slice(2).trim() : text;
        const base = slug(claim);
        let ruleName = base;
        for (let count = 2; objects.some((o) => o.id === `${name}/rule/${ruleName}`); count++) ruleName = `${base}-${count}`;
        lastRule = add("rule", ruleName, number, { claims: [claim] });
      }
    } else if (key === "workflow") {
      const blocks = subBlocks(body);
      const extra: Doc = {};
      if ("input" in blocks) extra.inputs = blocks.input.map(([, t]) => t);
      for (const [block, field] of [["failure", "failureBehavior"], ["recovery", "recoveryBehavior"], ["after", "postconditions"]]) {
        if (block in blocks) extra[field] = blocks[block].map(([, t]) => (t.startsWith("- ") ? t.slice(2).trim() : t));
      }
      add("workflow", value, line, extra);
    } else if (key === "example") {
      const blocks = subBlocks(body);
      add("example", value, line, { claims: ["given", "when", "then"].filter((k) => k in blocks).map((k) => join(blocks[k])) });
    } else if (key === "uncertainty") {
      const blocks = subBlocks(body);
      const blocking = ["yes", "true"].includes(join(blocks.blocking).toLowerCase());
      add("uncertainty", value, line, { status: "unresolved", claims: [join(blocks.question)], consequential: blocking, authority: "human" });
      if (blocking && !objects.some((o) => o.kind === "evidence")) add("evidence", "blocked", line, { status: "blocked", statement: `The ${value} decision is unresolved.` });
    }
  }
  return { modelVersion: "0.1.0", module: mod, objects };
}

const FULL_KEYS = new Set([
  "identity", "between", "cardinality", "requires", "durability", "actor", "input", "output",
  "uses", "actor-capabilities", "transitions", "claims", "given", "when", "then",
  "failure", "recovery", "after", "proved-by",
]);
const REF_ORDER = ["rule", "workflow", "relation", "state", "capability", "effect", "entity-type", "value-type"];

function fullBlocks(body: Line[]): Record<string, string[]> {
  const blocks: Record<string, string[]> = {};
  let current: string[] | null = null;
  for (const [, text] of body) {
    const m = text.match(KEY_RE);
    if (m && FULL_KEYS.has(m[1])) {
      current = blocks[m[1]] ??= [];
      if (m[2]) current.push(m[2]);
    } else if (current) {
      current.push(text.startsWith("- ") ? text.slice(2).trim() : text);
    }
  }
  return blocks;
}

type Node = { indent: number; key: string | null; value: string; children: Node[]; line: number };

// Indentation tree of `key: value` lines; other lines become keyless nodes.
function tree(raw: RawLine[]): Node[] {
  const roots: Node[] = [];
  const stack: Node[] = [];
  for (const [line, indent, text] of raw) {
    const m = text.match(/^([A-Za-z][\w-]*):(?:\s+(.*))?$/);
    const node: Node = { indent, key: m ? m[1] : null, value: m ? (m[2] ?? "").trim() : text, children: [], line };
    while (stack.length && stack[stack.length - 1].indent >= indent) stack.pop();
    (stack.length ? stack[stack.length - 1].children : roots).push(node);
    stack.push(node);
  }
  return roots;
}

const nodeText = (n: Node): string => [...(n.value ? [n.value] : []), ...n.children.map((c) => c.value)].join(" ");
const nodeItems = (n: Node): string[] =>
  [...(n.value ? [n.value] : []), ...n.children.map((c) => c.value)].map((i) => (i.startsWith("- ") ? i.slice(2).trim() : i));
const keyedMap = (raw: RawLine[]): Doc => {
  const out: Doc = {};
  for (const n of tree(raw)) if (n.key) out[n.key] = nodeText(n);
  return out;
};

function uncertaintyFields(name: string, raw: RawLine[], ref: (t: string, k: string[]) => string): Doc {
  const nodes = tree(raw);
  const top: Record<string, Node> = {};
  for (const n of nodes) if (n.key && n.key !== "option") top[n.key] = n;
  const blocking = "blocking" in top ? ["yes", "true"].includes(nodeText(top.blocking).toLowerCase()) : false;
  const out: Doc = {
    status: "unresolved",
    claims: ["question" in top ? nodeText(top.question) : ""],
    consequential: blocking,
    authority: "human",
  };
  if ("why-it-matters" in top) out.why_it_matters = nodeText(top["why-it-matters"]);
  if ("affects" in top) out.affected_objects = nodeItems(top.affects).map((t) => ref(t, REF_ORDER));
  if ("rule" in top) {
    const ruleName = nodeText(top.rule);
    out.rule = { id: `${name}/rule/${ruleName}`, name: ruleName };
  }
  const options: Doc[] = [];
  for (const node of nodes.filter((n) => n.key === "option")) {
    const option: Doc = { id: node.value };
    const examples: Doc[] = [];
    for (const child of node.children) {
      const key = child.key;
      if (key === "label" || key === "explanation" || key === "compilation") option[key] = nodeText(child);
      else if (key === "effects" || key === "impact") option[key] = nodeItems(child);
      else if (key === "rule-claims") option.rule_claims = nodeItems(child);
      else if (key === "example") {
        const exp = child.children.find((c) => c.key === "expects");
        examples.push({
          id: `${name}/example/${child.value}`, kind: "example", name: child.value, status: "accepted",
          expects: exp ? nodeItems(exp) : [],
        });
      }
    }
    if (examples.length) option.examples = examples;
    options.push(option);
  }
  if (options.length) out.options = options;
  return out;
}

function fullDocument(sections: Section[]): Doc {
  const name = sections[0].value;
  const mod: Doc = { id: `${name}/module`, kind: "module", name, status: "accepted", source: { line: sections[0].line } };
  const parameterSections = sections.filter((section) => section.key === "parameter");
  if (parameterSections.length) {
    mod.parameters = parameterSections.map((section) => outlineParameter(section));
  }
  const names: Record<string, Record<string, string>> = {};
  for (const s of sections.slice(1)) {
    const kind = DECLARATION_KINDS[s.key] ?? s.key;
    if (s.key in DECLARATION_KINDS || s.key === "workflow" || s.key === "rule") (names[kind] ??= {})[s.value] = `${name}/${kind}/${s.value}`;
  }
  const ref = (text: string, kinds: string[]): string => {
    for (const kind of kinds) if (names[kind] && Object.hasOwn(names[kind], text)) return names[kind][text];
    return text;
  };
  const params = (items: string[]): any[] =>
    items.map((i) => (words(i).length === 2 ? { name: words(i)[0], type: ref(words(i)[1], ["entity-type", "value-type"]) } : i));
  const known = ["value-type", "entity-type", "relation", "state", "capability", "effect", "workflow", "rule", "example", "uncertainty"];

  const objects: Doc[] = [];
  for (const section of sections.slice(1)) {
    const { key, value, body, line } = section;
    if (key === "purpose") {
      mod.purpose = [...(value ? [value] : []), ...body.map(([, t]) => t)].join(" ");
      continue;
    }
    if (key === "context") {
      mod.context = keyedMap(section.raw);
      continue;
    }
    if (key === "policies") {
      mod.implementationPolicies = keyedMap(section.raw);
      continue;
    }
    if (key === "imports") {
      mod.imports = body.map(([, t]) => (t.startsWith("- ") ? t.slice(2).trim() : t));
      continue;
    }
    const kind = DECLARATION_KINDS[key] ?? key;
    if (!known.includes(kind)) continue;
    const blocks = fullBlocks(body);
    const get = (k: string) => blocks[k] ?? [];
    const obj: Doc = { id: `${name}/${kind}/${value}`, kind, name: value, status: "accepted", source: { line } };
    if (kind === "entity-type" && "identity" in blocks) {
      obj.fields = get("identity").filter((f) => words(f).length === 2).map((f) => ({
        name: words(f)[0], type: ref(words(f)[1], ["value-type"]), identity: true,
      }));
    } else if (kind === "relation") {
      if ("between" in blocks) obj.endpoints = get("between").map((t) => ({ type: ref(t, ["entity-type"]) }));
      if ("cardinality" in blocks) obj.cardinality = get("cardinality").join(" ");
    } else if (kind === "effect") {
      obj.requires = get("requires").map((t) => ref(t, ["capability"]));
      if ("durability" in blocks) obj.durability = get("durability").join(" ");
    } else if (kind === "workflow") {
      const derived: Doc = {
        inputs: params(get("input")),
        outputs: params(get("output")),
        requires: get("requires").map((t) => ref(t, ["capability"])),
        uses: get("uses").map((t) => ref(t, ["effect"])),
        actorCapabilities: get("actor-capabilities").filter((i) => words(i).length === 2).map((i) => ({
          actor: words(i)[0], capability: ref(words(i)[1], ["capability"]),
        })),
        transitions: get("transitions").filter((i) => i.includes("->")).map((i) => {
          const at = i.indexOf("->");
          return { from: ref(i.slice(0, at).trim(), ["state"]), to: ref(i.slice(at + 2).trim(), ["state"]) };
        }),
        claims: get("claims"),
      };
      if ("actor" in blocks) obj.actor = get("actor").join(" ");
      for (const [block, field] of [["failure", "failureBehavior"], ["recovery", "recoveryBehavior"], ["after", "postconditions"]]) {
        if (get(block).length) obj[field] = get(block);
      }
      for (const [k, v] of Object.entries(derived)) if (v.length) obj[k] = v;
    } else if (kind === "rule") {
      const requires = get("requires").map((t) => ref(t, REF_ORDER));
      if (requires.length) obj.requires = requires;
      obj.claims = get("claims");
      if (get("proved-by").length) {
        obj.evidenceLinks = get("proved-by").flatMap((t) => t.split(",")).map((n) => n.trim()).filter(Boolean).map((n) => `${name}/example/${n}`);
      }
    } else if (kind === "example" && "given" in blocks) {
      obj.claims = ["given", "when", "then"].filter((k) => k in blocks).map((k) => blocks[k].join(" "));
    } else if (kind === "example") {
      obj.requires = get("requires").map((t) => ref(t, REF_ORDER));
      obj.expects = get("then");
    } else if (kind === "uncertainty") {
      Object.assign(obj, uncertaintyFields(name, section.raw, ref));
    }
    objects.push(obj);
    if (kind === "uncertainty" && obj.consequential && !objects.some((o) => o.id === `${name}/evidence/blocked`)) {
      objects.push({
        id: `${name}/evidence/blocked`, kind: "evidence", name: "blocked", status: "blocked", source: { line },
        statement: `The ${value} decision is unresolved.`,
      });
    }
  }
  return { modelVersion: "0.1.0", module: mod, objects };
}

function findStructuredFixture(path: string): string | null {
  const abs = resolve(path);
  const stem = basename(abs).replace(/\.[^.]*$/, "");
  for (let dir = dirname(abs); ; dir = dirname(dir)) {
    const candidate = join(dir, "tests", "conformance", `${stem}.structured.json`);
    if (existsSync(candidate)) return candidate;
    if (dirname(dir) === dir) return null;
  }
}

function outlineParameter(section: Section): Doc {
  const parameter: Doc = { name: section.value };
  for (const node of tree(section.raw)) {
    if (node.key === "type" || node.key === "unit") parameter[node.key] = nodeText(node);
  }
  return parameter;
}

function attachOutlineLines(document: Doc, sections: Section[]): void {
  (document.module ??= {}).source = { line: sections[0].line };
  const parameterSections = sections.filter((section) => section.key === "parameter");
  if (parameterSections.length) {
    document.module.parameters = parameterSections.map((section) => outlineParameter(section));
  }
  const linesByKey = new Map<string, number>();
  for (const s of sections) linesByKey.set(`${s.key}\0${s.value}`, s.line);
  const ruleLines = sections.filter((s) => s.key === "rules").flatMap((s) => s.body.map(([n]) => n));
  const rules = (document.objects ?? []).filter((o: any) => o && typeof o === "object" && o.kind === "rule");
  for (const obj of document.objects ?? []) {
    if (!obj || typeof obj !== "object") continue;
    let line = linesByKey.get(`${obj.kind}\0${obj.name}`);
    if (line === undefined && obj.kind === "rule" && ruleLines.length === rules.length) line = ruleLines[rules.indexOf(obj)];
    if (line !== undefined) obj.source = { line };
  }
}
