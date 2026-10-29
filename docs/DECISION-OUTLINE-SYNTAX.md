# Decision: Outline style is the main Orin syntax

## Decision

Orin is written in **outline style**: sections are `key: name` lines with
indented content, as in `examples/shared-tasks.minimal.orin` and
`examples/password-reset.orin`. Brace style (`module name { ... }`) is still
accepted, but it is legacy. New examples, docs and tools use outline style.

## Why

- It reads like a document. People who are not programmers can read, review
  and correct it.
- It carries only meaning (purpose, rules, examples, open questions). It has
  no code-like punctuation that suggests an implementation.
- The existing examples, the guide and the conformance fixtures already use
  it, so it is the style people actually meet.
- Its grammar is small and does not depend on any host language
  (`ORIN-SYNTAX-GRAMMAR.md`).

## Consequences

- `LANGUAGE-REFERENCE.md` and `ORIN-SYNTAX-GRAMMAR.md` describe outline
  style. Brace style is mentioned only as legacy.
- The loader keeps reading brace files, so nothing existing breaks. New
  features go into outline style first and may never reach brace style.
- Outline style cannot yet say everything brace style can (for example
  `context`, `policy`, plain entity fields). Those gaps are listed in the
  grammar document and must be closed in the loader before brace style can be
  removed.
- Tests and fixtures should be moved to outline style over time.

## Rejected alternative

**Brace style as the main syntax.** It was the first style the loader parsed
and it is easy to read by machine. It was rejected because it looks like code,
needs matching braces and quotes, and invites authors to think about
implementation instead of meaning.
