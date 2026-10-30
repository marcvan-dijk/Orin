import { BLOCK_KEYWORDS, parseOutline } from "./orinModel";

export interface Pos {
  line: number;
  character: number;
}
export interface Span {
  line: number;
  start: number;
  end: number;
}

const ID_CHAR = /[A-Za-z0-9_.\-]/;
const DECLARABLE = new Set<string>(BLOCK_KEYWORDS);

// Keys allowed inside blocks (line-style) in addition to the top-level block keywords.
export const FIELD_KEYS = [
  "purpose", "actor", "input", "requires", "claims", "context", "policies", "imports",
  "given", "when", "then", "question", "blocking", "option", "label", "description", "why",
] as const;

export interface Completion {
  label: string;
  insertText: string;
  kind: "keyword" | "id";
  detail?: string;
}

// Returns the identifier token under the cursor, or undefined.
export function idAt(text: string, pos: Pos): Span | undefined {
  const line = text.split(/\r?\n/)[pos.line];
  if (line === undefined) return undefined;
  let start = pos.character;
  let end = pos.character;
  while (start > 0 && ID_CHAR.test(line[start - 1])) start--;
  while (end < line.length && ID_CHAR.test(line[end])) end++;
  // Trim punctuation that is not part of an id (e.g. trailing ".").
  while (end > start && /[.\-]/.test(line[end - 1])) end--;
  while (start < end && /[.\-]/.test(line[start])) start++;
  if (start >= end || pos.character < start || pos.character > end) return undefined;
  return { line: pos.line, start, end };
}

export function tokenText(text: string, span: Span): string {
  return text.split(/\r?\n/)[span.line].slice(span.start, span.end);
}

export interface Declaration {
  id: string;
  kind: string;
  span: Span;
}

export function findDeclarations(text: string): Declaration[] {
  const lines = text.split(/\r?\n/);
  const result: Declaration[] = [];
  for (const s of parseOutline(text).symbols) {
    if (!DECLARABLE.has(s.kind)) continue;
    const line = lines[s.startLine];
    const idx = line.indexOf(s.name);
    // Skip inline list-style rules (`- text`) that are not id declarations.
    if (idx < 0 || !/^[A-Za-z0-9_.\-]+$/.test(s.name)) continue;
    result.push({ id: s.name, kind: s.kind, span: { line: s.startLine, start: idx, end: idx + s.name.length } });
  }
  return result;
}

export function findDefinition(text: string, pos: Pos): Span | undefined {
  const span = idAt(text, pos);
  if (!span) return undefined;
  const id = tokenText(text, span);
  return findDeclarations(text).find((d) => d.id === id)?.span;
}

export function findReferences(text: string, pos: Pos, includeDeclaration = true): Span[] {
  const span = idAt(text, pos);
  if (!span) return [];
  const id = tokenText(text, span);
  const decls = findDeclarations(text);
  if (!decls.some((d) => d.id === id)) return [];
  const isDecl = (s: Span) => decls.some((d) => d.id === id && d.span.line === s.line && d.span.start === s.start);
  const out: Span[] = [];
  text.split(/\r?\n/).forEach((line, i) => {
    let from = 0;
    while (true) {
      const at = line.indexOf(id, from);
      if (at < 0) break;
      from = at + id.length;
      const before = at > 0 ? line[at - 1] : "";
      const after = line[at + id.length] ?? "";
      const bounded = (c: string) => c === "" || !ID_CHAR.test(c);
      // A trailing "." or "-" ends a sentence, not an id.
      const afterOk = bounded(after) || (/[.\-]/.test(after) && bounded(line[at + id.length + 1] ?? ""));
      if (!bounded(before) || !afterOk) continue;
      const found = { line: i, start: at, end: at + id.length };
      if (includeDeclaration || !isDecl(found)) out.push(found);
    }
  });
  return out;
}

// Context for completion: keys at line start, ids after `requires:`-style lists or inline.
export function completionsAt(text: string, pos: Pos): Completion[] {
  const line = text.split(/\r?\n/)[pos.line] ?? "";
  const prefix = line.slice(0, pos.character);
  const indented = /^\s+/.test(prefix);
  if (/^\s*[A-Za-z-]*$/.test(prefix)) {
    const word = prefix.trim();
    const keys = indented ? FIELD_KEYS : BLOCK_KEYWORDS;
    return keys
      .filter((k) => k.startsWith(word))
      .map((k) => ({ label: `${k}:`, insertText: `${k}:`, kind: "keyword" as const }));
  }
  // After a `kind:` key (e.g. `rule:`) only a new name is expected; otherwise offer ids.
  if (/^[A-Za-z-]+:\s*[^\s]*$/.test(prefix) && DECLARABLE.has(prefix.split(":")[0])) return [];
  const word = /[A-Za-z0-9_.\-]*$/.exec(prefix)![0];
  return findDeclarations(text)
    .filter((d) => d.span.line !== pos.line && d.id.startsWith(word))
    .map((d) => ({ label: d.id, insertText: d.id, kind: "id" as const, detail: d.kind }));
}

export interface Snippet {
  name: string;
  prefix: string;
  body: string[];
  description: string;
}

export const SNIPPETS: Snippet[] = [
  {
    name: "New rule",
    prefix: "rule",
    body: ["rule: ${1:rule-id}", "  claims:", "    - ${2:What must always be true.}", ""],
    description: "Declare a rule",
  },
  {
    name: "New uncertainty",
    prefix: "uncertainty",
    body: [
      "uncertainty: ${1:uncertainty-id}",
      "  blocking: ${2|yes,no|}",
      "  question:",
      "    ${3:What is not decided yet?}",
      "  option: ${4:option-a}",
      "    description: ${5:What choosing this means.}",
      "  option: ${6:defer}",
      "    description: ${7:Decide later.}",
      "",
    ],
    description: "Declare an uncertainty with options",
  },
  {
    name: "New example",
    prefix: "example",
    body: [
      "example: ${1:example-id}",
      "  given:",
      "    ${2:The starting situation.}",
      "  when:",
      "    ${3:What happens.}",
      "  then:",
      "    ${4:What can be observed.}",
      "",
    ],
    description: "Declare an observable example",
  },
];
