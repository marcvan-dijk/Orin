# Orin VS Code Extension

This is the first small editor plugin for Orin. It provides `.orin` syntax
highlighting and an **Orin: Analyze Current File** command backed by the
optional Python reference parser.

## Try it

1. Open the repository root in VS Code.
2. Open `implementations/typescript/vscode-extension/` in a second VS Code
   window, or open its `package.json` and press `F5`.
3. Open `examples/password-reset.orin` in the Extension Development Host.
4. Run **Orin: Analyze Current File** from the Command Palette.

The Python launcher (`py`) must be available for semantic analysis. Syntax
highlighting works without Python.