# Orin VS Code Extension (Supporting Tooling)

This extension is supporting tooling for Orin authoring. It is not the Orin language and does not indicate feature completeness.

Current scope:

- `.orin` syntax highlighting
- **Orin: Analyze Current File** command backed by the optional Python reference checker

## Try it

1. Open `/home/runner/work/Orin/Orin` in VS Code.
2. Open `/home/runner/work/Orin/Orin/implementations/typescript/vscode-extension/` and run `F5`.
3. Open `/home/runner/work/Orin/Orin/examples/password-reset.orin` in the Extension Development Host.
4. Run **Orin: Analyze Current File**.

Notes:

- Syntax highlighting works without Python.
- The analysis command requires a Python launcher (`py`) in your environment.
