import * as path from "node:path";
import { execFile } from "node:child_process";
import * as vscode from "vscode";
import {
  findWorkflowAt,
  parseAgentOutput,
  parseOutline,
  workflowHover,
} from "./orinModel";

const SYMBOL_KINDS: Record<string, vscode.SymbolKind> = {
  module: vscode.SymbolKind.Module,
  workflow: vscode.SymbolKind.Function,
  rule: vscode.SymbolKind.Constant,
  example: vscode.SymbolKind.Event,
  uncertainty: vscode.SymbolKind.Variable,
};

type OrinDiagnostic = { code: string; message: string; line?: number };

export function activate(context: vscode.ExtensionContext): void {
  const diagnostics = vscode.languages.createDiagnosticCollection("orin");
  context.subscriptions.push(diagnostics);

  const analyze = vscode.commands.registerCommand(
    "orin.analyzeCurrentFile",
    () => {
      const document = vscode.window.activeTextEditor?.document;
      if (!document || document.languageId !== "orin") {
        void vscode.window.showInformationMessage("Open an .orin file first.");
        return;
      }

      const repository = path.resolve(context.extensionPath, "..", "..");
      const checker = path.join(
        repository,
        "implementations",
        "python",
        "check_orin.py",
      );
      execFile(
        "py",
        [checker, document.uri.fsPath],
        { cwd: repository },
        (error, stdout, stderr) => {
          if (error) {
            void vscode.window.showErrorMessage(
              `Orin analysis failed: ${stderr || error.message}`,
            );
            return;
          }
          try {
            const items = JSON.parse(stdout) as OrinDiagnostic[];
            diagnostics.set(
              document.uri,
              items.map((item) => {
                const line = Math.max(0, (item.line ?? 1) - 1);
                const range = new vscode.Range(
                  line,
                  0,
                  line,
                  document.lineAt(line).text.length,
                );
                const severity = item.code.startsWith("ORIN-E")
                  ? vscode.DiagnosticSeverity.Error
                  : vscode.DiagnosticSeverity.Warning;
                return new vscode.Diagnostic(
                  range,
                  `${item.code}: ${item.message}`,
                  severity,
                );
              }),
            );
            void vscode.window.showInformationMessage(
              `Orin analysis found ${items.length} issue(s).`,
            );
          } catch {
            void vscode.window.showErrorMessage(
              "Orin analysis returned invalid diagnostic data.",
            );
          }
        },
      );
    },
  );
  context.subscriptions.push(analyze);

  const selector: vscode.DocumentSelector = { language: "orin" };
  context.subscriptions.push(
    vscode.languages.registerDocumentSymbolProvider(selector, {
      provideDocumentSymbols(document) {
        return parseOutline(document.getText())
          .symbols.filter((s) => s.kind !== "module")
          .map((s) => {
            const range = new vscode.Range(
              s.startLine,
              0,
              s.endLine,
              document.lineAt(s.endLine).text.length,
            );
            const selection = document.lineAt(s.startLine).range;
            return new vscode.DocumentSymbol(
              s.name,
              s.kind,
              SYMBOL_KINDS[s.kind],
              range,
              selection,
            );
          });
      },
    }),
    vscode.languages.registerHoverProvider(selector, {
      provideHover(document, position) {
        const outline = parseOutline(document.getText());
        const workflow = findWorkflowAt(outline, position.line);
        if (!workflow) return undefined;
        return new vscode.Hover(
          new vscode.MarkdownString(workflowHover(outline, workflow)),
        );
      },
    }),
  );

  const status = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    50,
  );
  context.subscriptions.push(status);
  const output = vscode.window.createOutputChannel("Orin Agent");
  context.subscriptions.push(output);

  context.subscriptions.push(
    vscode.commands.registerCommand("orin.inspectWithAgent", () => {
      const document = vscode.window.activeTextEditor?.document;
      if (!document || document.languageId !== "orin") {
        void vscode.window.showInformationMessage("Open an .orin file first.");
        return;
      }
      const repository = path.resolve(context.extensionPath, "..", "..");
      const python = vscode.workspace
        .getConfiguration("orin")
        .get<string>("pythonPath", "python");
      execFile(
        python,
        ["-m", "tooling.python.orin_agent", "inspect", document.uri.fsPath],
        { cwd: repository },
        (error, stdout, stderr) => {
          if (error && !stdout) {
            void vscode.window.showErrorMessage(
              `Orin agent failed: ${stderr || error.message}`,
            );
            return;
          }
          const summary = parseAgentOutput(stdout);
          output.clear();
          output.appendLine(stdout);
          const blocked = summary.status === "blocked";
          status.text =
            summary.status === "ready"
              ? "$(check) Orin: ready"
              : blocked
                ? `$(error) Orin: blocked (${summary.decisions.length})`
                : "$(question) Orin: unknown";
          status.tooltip = summary.decisions.join("\n") || "No open decisions";
          status.command = "orin.inspectWithAgent";
          status.show();
          if (summary.decisions.length > 0) {
            output.show(true);
            void vscode.window.showWarningMessage(
              `Orin: ${summary.decisions.length} unresolved decision(s).`,
            );
          }
        },
      );
    }),
  );
}

export function deactivate(): void {}
