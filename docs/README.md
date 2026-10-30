# Orin documentation

This folder explains **Orin itself**. Application walkthroughs, domain
decisions, and example-specific findings belong in [examples](../examples/README.md).
Host-language setup and test commands belong with the
[implementations](../implementations/) and [tooling](../tooling/).

## Read and write Orin

| Document | Purpose |
| --- | --- |
| [Glossary](GLOSSARY.md) | Plain-language explanations of the core terms. |
| [Language reference](LANGUAGE-REFERENCE.md) | How to read and write the currently supported outline language, including the syntax choice and limitations. |
| [Exact grammar](ORIN-SYNTAX-GRAMMAR.md) | Precise outline syntax for parser and tool authors. |
| [Authoring with AI](AUTHORING-WITH-AI.md) | Turn a person's request into reviewable Orin without silently choosing consequential behavior; includes experimental collaboration tooling. |

For a hands-on start, use the
[password-reset walkthrough](../examples/docs/password-reset.md).
It is the primary end-to-end proof, not another language specification.

## Specifications

| Document | Authority and scope |
| --- | --- |
| [ORIN-0001: Intent and decision boundary](ORIN-0001-intent-spec.md) | Conceptual source for durable meaning and explicit consequential decisions. |
| [ORIN-0002: Language kernel](ORIN-0002-language-kernel.md) | Proposed language concepts and architecture; not a promise that every construct is implemented. |
| [ORIN-0004: Semantic model](ORIN-0004-semantic-model.md) | Deferred foundational specification, not current implementation work. |

For what the tools actually accept today, start with the language reference
and grammar. For what has been demonstrated, use the
[conformance evidence index](../tests/conformance/README.md).

## Develop Orin

| Document | Purpose |
| --- | --- |
| [Contributing](../CONTRIBUTING.md) | Repository boundaries, placement rules, and validation commands. |
| [ORIN-0003: Implementation log](ORIN-0003-language-improvement-plan.md) | The single active tracker: completed increments and the exact next step. Its path stays stable for contributor tooling. |
| [Development backlog](development/BACKLOG.md) | Deferred analysis, retained MVP conclusions, and optional internal tooling notes. |
| [Evolution roadmap](development/ORIN-0006-next-evolution-roadmap.md) | Historical phase reasoning and longer-term context, not a competing task list. |

## Keep this structure clear

- Language rules and authoring guidance stay here; application-specific
  material stays under `examples/`.
- Extend the existing topic guide before creating another document.
- Record status only in ORIN-0003. Example findings are evidence, not an
  automatic queue of language features.
- Keep programs and conformance fixtures readable without installing a host
  runtime. The [repository README](../README.md#try-it) lists tool requirements.
