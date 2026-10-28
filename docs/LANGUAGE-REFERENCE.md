# Orin Language Reference

This is a short reference for the `.orin` language as the Python loader
(`implementations/python/orin_parser.py`) reads it today. It lists what works
now, not what is planned.

## Two writing styles

1. **Outline style** (indented labels like `module: password-reset`). Used by
   `examples/password-reset.orin` and described in `ORIN-SYNTAX-GUIDE.md`. The
   loader does **not** read this style in general. It only loads that one
   example file, by matching its known lines and using the matching JSON file
   in `tests/conformance/`.
2. **Block style** (`module name { ... }`). This is the style the loader
   really parses. Everything below, and every snippet, uses it.

Block style rules:

- One declaration or attribute per line. Blank lines and lines starting with
  `//` are ignored.
- Text values are in double quotes: `purpose "Reset passwords safely."`
- Names use letters, digits, `_`, `.` and `-`.
- The file starts with `module <name> {`. Without it you get `ORIN-P001`.
- Each object gets an id: `<module>/<kind>/<name>`.

## Module-level lines

| Line | Meaning |
|---|---|
| `purpose "..."` | Why the module exists. |
| `import <name>` | Records an import (kept as text only). |
| `context { repository "..." risk "..." }` | Extra facts, one per line. Only `repository` and `risk` are allowed (`ORIN-P006`). |
| `policy implementation { ... }` | Implementation preferences, one per line: `optimize-for`, `prefer`, `require`, `deploy-to`, each with a quoted value (`ORIN-P007`). |
| `scope ... {` , `risk ... {`, `role ...` | Accepted and ignored. |

## Section kinds

Single-line (no braces): `type <name>`, `state <name>`,
`capability <name>`, `evidence <name> "statement"`.

Block (`kind name {` ... `}`): `entity`, `relation`, `rule`, `workflow`,
`example`, `uncertainty`, `target`, `effect`.

| Kind | Lines that work inside |
|---|---|
| `entity` | `field <name> <value-type> [identity]` |
| `relation` | `from <entity>`, `to <entity>`, `cardinality <one-to-one\|one-to-many\|many-to-one\|many-to-many>` |
| `workflow` | `input <name> <type>`, `output <name> <type>`, `transition <state> -> <state>`, `requires <capability>`, `uses <effect>`, `actor <name>`, `bind <actor> <capability>` |
| `effect` | `requires <capability>`, `durability <strong\|eventual>` |
| `rule`, `example`, `uncertainty`, `target` | text lines (below) |

Text lines, allowed in any block: `purpose`, `guarantee`, `question`,
`outcome`, `recovery`, `given`, `when`, `then`, `impact` (all take a quoted
text), `severity` (quoted), `authority` (unquoted). `budget ...` is ignored.
Any other line gives `ORIN-P005`. A `{` block that is not closed gives
`ORIN-P003`; a line that fits nothing gives `ORIN-P002`.

Short names such as `Order` are turned into full ids for you. Referring to a
name that is not declared gives `ORIN-E007` or a type error (see below).

## Rules, examples, uncertainties, decisions

**Rule** — something that must always be true. Write each statement as a
`guarantee`.

**Example** — one observable case. Use `given`, `when`, `then`.

**Uncertainty** — a question nobody answered yet. In the loader, every
`uncertainty` block is *consequential* (it blocks readiness) as long as it is
in the file.

**Decision** — there is no `decision` keyword. To decide, answer the question
and remove the `uncertainty` block. Write the answer as a `rule` or
`example`.

```orin
module demo.shop {
  purpose "Sell items."
  type Email
  type Sku
  state placed
  state paid
  entity Order {
    field id Sku identity
    field contact Email
  }
  workflow pay {
    input order Order
    transition placed -> paid
  }
  rule no-double-pay {
    guarantee "An order is charged once."
  }
  example paid-once {
    given "An order is placed."
    when "The buyer pays."
    then "The order is paid."
  }
  uncertainty refunds {
    question "Are refunds allowed after 30 days?"
    impact "Support load"
  }
}
```

A rule that says both "X" and "not X" gives `ORIN-E046`.

## Policy and context

```orin
module demo.policy {
  context {
    repository "github.com/example/shop"
    risk "medium"
  }
  policy implementation {
    optimize-for "cost"
    deploy-to "eu-west"
  }
}
```

Each policy line shows up as an `ORIN-R301` info message. It never blocks.

## Check errors (ORIN-E…)

Run `python implementations/python/check_orin.py file.orin`. Parse problems
come back as `ORIN-P000` with the `ORIN-Pxxx` text inside.

| ID | Problem |
|---|---|
| E001–E003 | Bad document shape (objects not a list, object not an object, id not a string). |
| E004, E005 | Duplicate object id / module id. |
| E006, E007 | A reference field is not a list / points to an unknown id. |
| E008 | Unsupported section kind. |
| E020 | Entity has no fields. |
| E021 | Entity needs exactly one `identity` field. |
| E022, E023 | Entity field has no name / name used twice. |
| E024 | Entity field type is not a `type`. |
| E025 | Relation needs exactly two endpoints (`from`, `to`). |
| E026 | Relation endpoint is not an `entity`. |
| E027 | Bad `cardinality`. |
| E028–E030 | Workflow inputs/outputs: not a list / no name / type is not a `type` or `entity`. |
| E031–E034 | Transition problems: not a list, same state on both sides, missing side, or not a `state`. |
| E035 | `requires` target is not a `capability`. |
| E036 | `uses` target is not an `effect`. |
| E037 | Actor is not bound to every capability the workflow (or its effects) needs. Only checked when `bind` is used. |
| E038 | Bad actor binding. |
| E039, E040 | Effect named `persistent-entity-store.*` has no / an invalid `durability`. |
| E041 | An unresolved consequential `uncertainty`. |
| E042, E043, E045 | An `effect` / `capability` / `relation` is never used by a workflow, rule or example. |
| E044 | A `state` is not used in any transition (checked only if some transition exists). |
| E046 | A rule contradicts itself. |

## Readiness (ORIN-R…)

`readiness_report()` gives a status:

- `fail` — there are check errors.
- `blocked` — an unresolved uncertainty, or at least one blocking `R` item.
- `eligible` — nothing blocks.

Blocking items ("required decisions"):

| ID | Needed on | Missing field |
|---|---|---|
| R001, R002 | `capability` | owner, scope |
| R010, R011, R031, R032 | `effect` | failure modes, data access, inputs, outputs |
| R020, R021, R050 | `workflow` | failure behavior, recovery behavior, postconditions |
| R030 | `entity` that a workflow outputs | lifecycle |
| R040 | every `rule` | linked evidence |
| R201 | `uncertainty` | blocks when unresolved |

Non-blocking: R101 (relation `deletionBehavior` unset, default `retain`),
R102 (effect `retryPolicy` unset, default `none`), R301 (policy choice).
R900 means the document structure is broken.

**Important limit today:** block style cannot yet write the fields behind
R001–R050 (for example `failureBehavior`, `evidenceLinks`). `recovery` and
`outcome` lines become plain claims, not those fields. So a block-style
workflow or rule always reports these `R` items; only the JSON form
(`tests/conformance/*.json`) can satisfy them.

## Outline example

`examples/password-reset.orin` uses labels `module:`, `purpose:`, `rules:`
(with `-` items), `workflow:` (`input:`, `steps:`), `example:` (`given:`,
`when:`, `then:`) and `uncertainty:` (`blocking: yes`, `question:`). Because
it has an open, blocking question, the example is *blocked*, not ready.
