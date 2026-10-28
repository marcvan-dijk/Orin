# Orin VS Code Extension (Supporting Tooling)

This extension is supporting tooling for Orin authoring. It is not the Orin language and does not indicate feature completeness.

Current scope:

- `.orin` syntax highlighting
- **Orin: Analyze Current File** command backed by the optional Python reference checker
- **Orin: Inspect with Orin Agent** command and status bar item
- Problems-panel warnings for each unresolved decision reported by `python -m tooling.python.orin_agent inspect <file>` (refreshed on open and save), anchored to the matching `uncertainty:` block
- Quick fix **Show decision options** on those warnings, listing the agent's options (selecting one does not edit the file)

## Settings

- `orin.pythonPath` (default `python`): Python executable used to run the agent from the repository root.

## Develop

```
cd tooling/vscode-extension
npm ci
npm run compile
npm test
```

`node_modules/` and `out/` are git-ignored.

## Try it

1. Open the repository root in VS Code.
2. Open `tooling/vscode-extension/` and run `F5`.
3. Open `examples/password-reset.orin` in the Extension Development Host.
4. Run **Orin: Analyze Current File**.

Notes:

- Syntax highlighting works without Python.
- The analysis command currently invokes the Windows Python launcher (`py`).
- The analysis command is therefore currently Windows-oriented; on macOS/Linux, syntax highlighting remains available while analyzer portability is a follow-up task.
