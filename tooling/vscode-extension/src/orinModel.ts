export type OrinSymbolKind = "module" | "workflow" | "rule" | "example" | "uncertainty";

export interface OrinSymbol {
  kind: OrinSymbolKind;
  name: string;
  startLine: number;
  endLine: number;
  purpose?: string;
  actor?: string;
}

export interface OrinOutline {
  modulePurpose?: string;
  symbols: OrinSymbol[];
}

const BLOCK = /^(module|workflow|example|uncertainty):\s*(.*?)\s*$/;
const FIELD = /^\s+(purpose|actor):\s*(.*?)\s*$/;

function isTopLevel(line: string): boolean {
  return /^[A-Za-z]/.test(line);
}

// Line-based outline; all line numbers are zero-based.
export function parseOutline(text: string): OrinOutline {
  const lines = text.split(/\r?\n/);
  const symbols: OrinSymbol[] = [];
  let modulePurpose: string | undefined;
  let current: OrinSymbol | undefined;
  let section: string | undefined;
  let fieldKey: "purpose" | "actor" | undefined;

  const close = (end: number) => {
    if (current) {
      let last = end;
      while (last > current.startLine && lines[last].trim() === "") last--;
      current.endLine = last;
    }
    current = undefined;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (isTopLevel(line)) {
      close(i - 1);
      fieldKey = undefined;
      section = undefined;
      const block = BLOCK.exec(line);
      if (block) {
        current = { kind: block[1] as OrinSymbolKind, name: block[2], startLine: i, endLine: i };
        symbols.push(current);
        continue;
      }
      const header = /^([a-z-]+):\s*$/.exec(line);
      if (header) section = header[1];
      continue;
    }
    if (line.trim() === "") continue;

    if (section === "purpose" && !current) {
      modulePurpose = modulePurpose ? `${modulePurpose} ${line.trim()}` : line.trim();
    } else if (section === "rules" && !current) {
      const rule = /^\s+-\s+(.*\S)\s*$/.exec(line);
      if (rule) {
        symbols.push({ kind: "rule", name: rule[1], startLine: i, endLine: i });
      }
    } else if (current?.kind === "workflow") {
      const field = FIELD.exec(line);
      if (field) {
        fieldKey = field[1] as "purpose" | "actor";
        if (field[2]) current[fieldKey] = field[2];
      } else if (fieldKey && /^\s{4,}\S/.test(line)) {
        current[fieldKey] = `${current[fieldKey] ?? ""} ${line.trim()}`.trim();
      } else {
        fieldKey = undefined;
      }
    }
  }
  close(lines.length - 1);
  return { modulePurpose, symbols };
}

export function findWorkflowAt(outline: OrinOutline, line: number): OrinSymbol | undefined {
  return outline.symbols.find(
    (s) => s.kind === "workflow" && line >= s.startLine && line <= s.endLine,
  );
}

export function workflowHover(outline: OrinOutline, workflow: OrinSymbol): string {
  const parts = [`**workflow** \`${workflow.name}\``];
  const purpose = workflow.purpose ?? outline.modulePurpose;
  if (purpose) {
    parts.push(`**Purpose:** ${purpose}${workflow.purpose ? "" : " _(module)_"}`);
  }
  if (workflow.actor) parts.push(`**Actor:** ${workflow.actor}`);
  return parts.join("\n\n");
}

export interface AgentSummary {
  status: "ready" | "blocked" | "unknown";
  decisions: string[];
}

// Parses `orin_agent inspect` text output.
export function parseAgentOutput(output: string): AgentSummary {
  const compilation = /^Compilation:\s*(\S+)/m.exec(output)?.[1];
  const validation = /^Validation:\s*(\S+)/m.exec(output)?.[1];
  const states = [compilation, validation].filter((s): s is string => !!s);
  let status: AgentSummary["status"] = "unknown";
  if (states.some((s) => s === "blocked")) status = "blocked";
  else if (states.length > 0 && states.every((s) => s === "ready")) status = "ready";
  const decisions: string[] = [];
  const re = /^\d+\.\s+(\S+)\s*\n\s+Question:\s*(.*)$/gm;
  let m: RegExpExecArray | null;
  while ((m = re.exec(output))) decisions.push(`${m[1]}: ${m[2]}`);
  return { status, decisions };
}

export interface AgentOption {
  id: string;
  description: string;
  whyChoose?: string;
  compilation?: string;
}

export interface AgentDecision {
  id: string;
  question: string;
  whyItMatters?: string;
  options: AgentOption[];
}

// Parses the numbered decision blocks of `orin_agent inspect` text output.
export function parseDecisions(output: string): AgentDecision[] {
  const decisions: AgentDecision[] = [];
  let decision: AgentDecision | undefined;
  let option: AgentOption | undefined;
  let inOptions = false;
  for (const line of output.split(/\r?\n/)) {
    const head = /^\d+\.\s+(\S+)\s*$/.exec(line);
    if (head) {
      decision = { id: head[1], question: "", options: [] };
      decisions.push(decision);
      option = undefined;
      inOptions = false;
      continue;
    }
    if (!decision) continue;
    let m: RegExpExecArray | null;
    if ((m = /^\s{3}Question:\s*(.*)$/.exec(line))) decision.question = m[1];
    else if ((m = /^\s{3}Why it matters:\s*(.*)$/.exec(line))) decision.whyItMatters = m[1];
    else if (/^\s{3}Options:\s*$/.test(line)) inOptions = true;
    else if (inOptions && (m = /^\s{3}-\s+(\S+?):\s*(.*)$/.exec(line))) {
      option = { id: m[1], description: m[2] };
      decision.options.push(option);
    } else if (inOptions && option && (m = /^\s{5}Why choose it:\s*(.*)$/.exec(line))) {
      option.whyChoose = m[1];
    } else if (inOptions && option && (m = /^\s{5}Compilation:\s*(.*)$/.exec(line))) {
      option.compilation = m[1];
    }
  }
  return decisions;
}

// Finds the line of the `uncertainty: <name>` block a decision id refers to.
export function findUncertaintyLine(source: string, decisionId: string): number {
  const name = decisionId.split("/").pop() ?? decisionId;
  const lines = source.split(/\r?\n/);
  const index = lines.findIndex((l) => l.trim() === `uncertainty: ${name}`);
  return index >= 0 ? index : 0;
}
