import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, checkedModuleId, readiness, sanitizeId } from "./sanitize.ts";

type Obj = Record<string, any>;

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : []);
const short = (id: unknown) => sanitizeId(String(id).split("/").pop() ?? "");

// Unique, valid TypeScript identifier suffix for an object name.
function identFor(prefix: string, name: string, used: Set<string>): string {
  const base = `${prefix}_${name.replace(/[^A-Za-z0-9]/g, "_")}`;
  let id = base;
  for (let i = 2; used.has(id); i++) id = `${base}_${i}`;
  used.add(id);
  return id;
}

// Generic, model-driven generator. Works for any eligible model: rules become functions that throw
// NotImplementedRule until a hook is supplied, workflows with transitions become a state machine,
// and examples become checks that run through supplied hooks.
export function generateGeneric(model: SemanticModel): string {
  const moduleId = checkedModuleId(model);
  const gates = readiness(model);
  if (gates.compilation !== "eligible") {
    throw new GenerationRefused(
      `model is ${gates.compilation}; unresolved: ${gates.blockingUnresolved.join(", ") || "none"}`,
    );
  }
  const objects: Obj[] = Array.isArray(model.document.objects) ? model.document.objects : [];
  const ofKind = (kind: string) => objects.filter((o) => o.kind === kind && typeof o.id === "string");
  const used = new Set<string>();

  const rules = ofKind("rule").map((o) => ({
    id: o.id, name: short(o.id), fn: identFor("rule", short(o.id), used), claims: strings(o.claims),
  }));
  const workflows = ofKind("workflow").map((o) => ({
    id: o.id, name: short(o.id), inputs: (Array.isArray(o.inputs) ? o.inputs : []).map((i: any) =>
      typeof i === "string" ? i : String(i?.name ?? "")),
    transitions: (Array.isArray(o.transitions) ? o.transitions : [])
      .filter((t: any) => t && typeof t === "object")
      .map((t: any) => ({ from: short(t.from), to: short(t.to) })),
  }));
  const examples = ofKind("example").map((o) => ({
    id: o.id, name: short(o.id), steps: strings(o.claims), expects: strings(o.expects),
  }));
  const open = ofKind("uncertainty")
    .filter((o) => o.status === "unresolved")
    .map((o) => ({ id: o.id, claims: strings(o.claims) }));
  const initial = workflows.flatMap((w) => w.transitions.map((t: any) => t.from))
    .find((s: string) => !workflows.some((w) => w.transitions.some((t: any) => t.to === s)));
  const data = { rules, workflows, examples, openUncertainties: open, initialState: initial ?? null };

  return `// Generated from ${moduleId}. Do not edit; regenerate instead.
// Generic model-driven module: rules are functions, workflows are state machines, examples are checks.
// Anything the generator cannot derive throws NotImplementedRule until a hook is supplied.

export const MODULE_ID = ${JSON.stringify(moduleId)};
export const MODEL = ${JSON.stringify(data, null, 2)} as const;

export class NotImplementedRule extends Error {
  readonly ruleId: string;
  readonly claims: readonly string[];
  constructor(ruleId: string, claims: readonly string[]) {
    super(\`NotImplementedRule: \${ruleId}: \${claims.join(" ")}\`);
    this.ruleId = ruleId;
    this.claims = claims;
  }
}

export type Hook = (...args: any[]) => any;
export type Hooks = Record<string, Hook | undefined>;

function hookOrThrow(hooks: Hooks, id: string, claims: readonly string[]): Hook {
  const hook = hooks[id];
  if (typeof hook !== "function") throw new NotImplementedRule(id, claims);
  return hook;
}

${rules.map((r) => `export function ${r.fn}(hooks: Hooks, ...args: any[]): any {
  return hookOrThrow(hooks, ${JSON.stringify(r.id)}, ${JSON.stringify(r.claims)})(...args);
}`).join("\n\n")}

export const RULE_FUNCTIONS: Record<string, (hooks: Hooks, ...args: any[]) => any> = {
${rules.map((r) => `  ${JSON.stringify(r.id)}: ${r.fn},`).join("\n")}
};

// Moves state along the workflow's declared transitions. A workflow without transitions needs a hook.
export function runWorkflow(workflowId: string, state: string | null, hooks: Hooks = {}, ...args: any[]): any {
  const wf = MODEL.workflows.find((w) => w.id === workflowId);
  if (!wf) throw new Error(\`unknown workflow: \${workflowId}\`);
  if (wf.transitions.length === 0) {
    return hookOrThrow(hooks, workflowId, [\`workflow \${wf.name} has no declared transitions\`])(...args);
  }
  const next = wf.transitions.find((t) => t.from === state);
  if (!next) return { ok: false, failure: \`invalid-transition.\${state}\`, state };
  return { ok: true, state: next.to };
}

export interface CheckResult { example: string; passed: boolean; }

// Runs one example through hooks[exampleId](example); the hook returns true when the example holds.
export function checkExample(exampleId: string, hooks: Hooks = {}): CheckResult {
  const ex = MODEL.examples.find((e) => e.id === exampleId);
  if (!ex) throw new Error(\`unknown example: \${exampleId}\`);
  const hook = hookOrThrow(hooks, exampleId, [...ex.steps, ...ex.expects]);
  return { example: ex.name, passed: hook(ex) === true };
}

export function checkAllExamples(hooks: Hooks = {}): CheckResult[] {
  return MODEL.examples.map((e) => checkExample(e.id, hooks));
}
`;
}
