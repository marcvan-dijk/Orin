import { SemanticModel } from "../orin_model.ts";
import { GenerationRefused, checkedModuleId, readiness } from "./sanitize.ts";

export const NO_ELIGIBLE_APPROVER_UNCERTAINTY = "finance.expense-approval/uncertainty/no-eligible-approver";

export type NoEligibleApproverDecision = { noEligibleApprover: "stay-submitted" };

function resolved(model: SemanticModel): SemanticModel {
  const next = JSON.parse(JSON.stringify(model.document));
  if (Array.isArray(next.unresolved)) {
    next.unresolved = next.unresolved.filter((id: unknown) => id !== NO_ELIGIBLE_APPROVER_UNCERTAINTY);
  }
  return new SemanticModel(next);
}

// Emits a standalone, dependency-free TypeScript module. Output is a pure
// function of (model identity, decision) and contains no timestamps.
export function generateExpenseApproval(model: SemanticModel, decision: NoEligibleApproverDecision): string {
  if (decision?.noEligibleApprover !== "stay-submitted") {
    throw new GenerationRefused('expense-approval decision requires noEligibleApprover: "stay-submitted"');
  }
  const moduleId = checkedModuleId(model);
  const gates = readiness(resolved(model));
  if (gates.compilation !== "eligible") {
    throw new GenerationRefused(
      `model is ${gates.compilation}; unresolved: ${gates.blockingUnresolved.join(", ") || "none"}`,
    );
  }
  return `// Generated from ${moduleId}. Do not edit.
// Resolved ${NO_ELIGIBLE_APPROVER_UNCERTAINTY}: ${decision.noEligibleApprover}.

export const NO_ELIGIBLE_APPROVER = "${decision.noEligibleApprover}" as const;

export interface Approver {
  limit: number;
  isSubmitter: boolean;
}

export interface DecisionResult {
  expense: "submitted" | "approved" | "rejected";
  approval?: "refused";
  rejection?: "refused";
  reason?: string;
  reasonVisibleToSubmitter?: true;
}

export class Expense {
  state: "submitted" | "approved" | "rejected";
  reason = "";
  amount: number;

  constructor(amount: number, state: "submitted" | "approved" | "rejected" = "submitted") {
    this.amount = amount;
    this.state = state;
  }

  approve(approver: Approver): DecisionResult {
    if (this.state !== "submitted" || approver.isSubmitter || approver.limit < this.amount) {
      return { expense: this.state, approval: "refused" };
    }
    this.state = "approved";
    return { expense: "approved" };
  }

  reject(approver: Approver, reason: string): DecisionResult {
    if (this.state !== "submitted" || approver.isSubmitter) {
      return { expense: this.state, rejection: "refused" };
    }
    this.state = "rejected";
    this.reason = reason;
    return { expense: "rejected", reason, reasonVisibleToSubmitter: true };
  }
}
`;
}
