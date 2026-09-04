import * as path from "node:path";
import { execFile } from "node:child_process";
import * as vscode from "vscode";

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
}

export function deactivate(): void {}
