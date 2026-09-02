# Orin Project Instructions

- Keep the `.ori` language, semantic model, conformance fixtures, and file
  formats independent of any host implementation language.
- Do not require installing Python, Node, .NET, or another runtime to author or
  reason about `.ori` programs or to inspect `tests/conformance/`.
- If executable code is needed, place it under a clearly named host-language
  subfolder such as `implementations/python/` or `implementations/typescript/`.
  Keep its tests, dependencies, and setup instructions in that subfolder.
- Do not put host-language imports, package metadata, or test runners in the
  shared `orin/` language namespace or in `tests/conformance/`.
- Prefer standard-library or dependency-free implementations for experiments;
  never turn a host runtime installation into a prerequisite without an
  explicit user decision.
- Record completed work and the exact next step in
  `docs/ORIN-0003-language-improvement-plan.md` after each implementation
  increment.
- When continuing the implementation plan, mark finished tasks as `[done]` and
  add new tasks when the work reveals additional required steps.
