import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, generatePasswordReset } from "./generate_password_reset.ts";
import { generateExpenseApproval } from "./generate_expense_approval.ts";
import { generateGeneric } from "./generic.ts";
import { checkedModuleId } from "./sanitize.ts";

export class CliError extends Error {}

const GENERATORS: Record<string, { file: string; run: (m: SemanticModel, d: any) => string }> = {
  "account.password-reset/module": { file: "password_reset.generated.ts", run: generatePasswordReset },
  "finance.expense-approval/module": { file: "expense_approval.generated.ts", run: generateExpenseApproval },
};

// Pure: returns the output file name and source, or throws CliError / GenerationRefused.
export function generate(modelText: string, decisionText: string): { file: string; source: string } {
  let model: SemanticModel;
  try {
    model = SemanticModel.fromJsonText(modelText);
  } catch (e) {
    throw new CliError(`invalid model: ${(e as Error).message}`);
  }
  let decision: unknown;
  try {
    decision = JSON.parse(decisionText);
  } catch (e) {
    throw new CliError(`invalid decision JSON: ${(e as Error).message}`);
  }
  const id = String(model.document.module?.id ?? "");
  const gen = GENERATORS[id];
  if (!gen) {
    const stem = checkedModuleId(model).replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "") || "model";
    return { file: `${stem}.generated.ts`, source: generateGeneric(model) };
  }
  return { file: gen.file, source: gen.run(model, decision) };
}

// Exit codes: 0 ok, 1 generation refused, 2 usage/input error.
export async function main(argv: string[]): Promise<number> {
  const { readFileSync, mkdirSync, writeFileSync } = await import("node:fs");
  const { resolve } = await import("node:path");
  const [modelPath, decisionPath, outDir] = argv;
  if (!modelPath || !decisionPath || !outDir || argv.length > 3) {
    console.error("usage: cli.ts <model.json> <decision.json> <outdir>");
    return 2;
  }
  try {
    let modelText: string, decisionText: string;
    try {
      modelText = readFileSync(modelPath, "utf-8");
      decisionText = readFileSync(decisionPath, "utf-8");
    } catch (e) {
      throw new CliError(`cannot read input: ${(e as Error).message}`);
    }
    const { file, source } = generate(modelText, decisionText);
    mkdirSync(outDir, { recursive: true });
    const target = resolve(outDir, file);
    writeFileSync(target, source);
    console.log(target);
    return 0;
  } catch (e) {
    if (e instanceof GenerationRefused) {
      console.error(`refused: ${e.message}`);
      return 1;
    }
    if (e instanceof CliError) {
      console.error(`error: ${e.message}`);
      return 2;
    }
    throw e;
  }
}

if (import.meta.main) {
  process.exitCode = await main(process.argv.slice(2));
}
