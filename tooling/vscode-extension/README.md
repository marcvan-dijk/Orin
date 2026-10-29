# Orin VS Code Extension (Supporting Tooling)

This extension is supporting tooling for Orin authoring. It is not the Orin language and does not indicate feature completeness.

Current scope:

- `.orin` syntax highlighting
- **Orin: Analyze Current File** command backed by the optional Python reference checker
- **Orin: Inspect with Orin Agent** command and status bar item
- Problems-panel warnings for each unresolved decision reported by `python -m tooling.python.orin_agent inspect <file>` (refreshed on open and save), anchored to the matching `uncertainty:` block
- Quick fix **Show decision options** on those warnings, listing the agent's options ; selecting one runs `orin_agent decide`, writes the revised model (default `<name>.resolved.json`, chosen via a save dialog), opens it, and refreshes diagnostics and the ready/blocked status bar

## Settings

- `orin.pythonPath` (default `python`): Python executable used to run the agent from the repository root.

## Workspace Trust

In untrusted workspaces the extension runs in limited mode: highlighting, outline and hover work, but the agent and checker (which run Python from the workspace) are disabled, and `orin.pythonPath` is ignored. Trusting the workspace re-enables them.

## Develop

```
cd tooling/vscode-extension
npm ci
npm run compile
npm test
```

`node_modules/` and `out/` are git-ignored.

## Package without vsce

A `.vsix` is a zip with an `extension/` folder. With no extra dependencies:

```
cd tooling/vscode-extension
npm run compile
mkdir -p .vsix/extension
cp -r package.json README.md language-configuration.json syntaxes out .vsix/extension/
printf '<?xml version="1.0" encoding="utf-8"?><PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011"><Metadata><Identity Language="en-US" Id="orin-language" Version="0.0.1" Publisher="orin"/><DisplayName>Orin Language</DisplayName></Metadata><Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/></Assets></PackageManifest>' > .vsix/extension.vsixmanifest
printf '<?xml version="1.0" encoding="utf-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension=".json" ContentType="application/json"/><Default Extension=".js" ContentType="application/javascript"/><Default Extension=".map" ContentType="application/json"/><Default Extension=".md" ContentType="text/markdown"/><Default Extension=".vsixmanifest" ContentType="text/xml"/></Types>' > '.vsix/[Content_Types].xml'
(cd .vsix && zip -r ../orin-language-0.0.1.vsix .)
code --install-extension orin-language-0.0.1.vsix
rm -rf .vsix
```

Alternatively, copy this folder (after `npm run compile`) into `~/.vscode/extensions/orin-language-0.0.1/` and reload VS Code. The extension calls the repository's Python tooling by relative path, so it must stay inside an Orin checkout.

`.vsix` files and `.vsix/` are build output; do not commit them.

## Try it

1. Open the repository root in VS Code.
2. Open `tooling/vscode-extension/` and run `F5`.
3. Open `examples/password-reset.orin` in the Extension Development Host.
4. Run **Orin: Analyze Current File**.

Notes:

- Syntax highlighting works without Python.
- The analysis command currently invokes the Windows Python launcher (`py`).
- The analysis command is therefore currently Windows-oriented; on macOS/Linux, syntax highlighting remains available while analyzer portability is a follow-up task.
