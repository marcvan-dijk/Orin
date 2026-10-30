# Orin Language Reference

This is a short guide to writing `.orin` files in **outline style**, as the
Python loader (`implementations/python/orin_parser.py`) reads it today. The
exact grammar is in `ORIN-SYNTAX-GRAMMAR.md`. Why outline style is the main
style is in `DECISION-OUTLINE-SYNTAX.md`. Brace style (`module name { ... }`)
still loads but is legacy and is not described here.

Orin files say what a program must do: its purpose, its rules, examples you
can observe, and questions nobody has answered yet. They do not say how to
build it.

## The basics

- The first line is `module: <name>`.
- A section starts at the left edge with `key: name` or `key:`.
- Indented lines belong to the section above. How far you indent does not
  matter.
- Blank lines and lines starting with `//` are ignored.
- A line at the left edge that is not `key: ...` gives `ORIN-P010`. A file
  that does not start with `module:` gives `ORIN-P001`.

## Two levels of detail

The loader looks at which sections you used.

- **Simple**: only `purpose`, `rules`, `workflow`, `example`, `uncertainty`.
  This is the easiest way to start. Rules and workflow steps are plain text.
- **Detailed**: as soon as you use `type`, `entity`, `relation`, `state`,
  `capability`, `effect` or `rule:` (one rule per section), the file is read
  as a checked model. Names must point to things you declared.

## Simple sections

```orin
module: demo.shop

purpose:
  Sell items to customers and take payment once.

rules:
  - An order is charged at most once.
  - A paid order cannot be paid again.

workflow: pay-order
  input:
    order
  steps:
    check the order is placed
    charge the customer
    mark the order paid

example: pays-once
  given:
    An order that is placed.
  when:
    The buyer pays.
  then:
    The order is paid.

uncertainty: refund-window
  blocking: yes
  question:
    Are refunds allowed after 30 days?
```

| Section | What it holds |
|---|---|
| `purpose:` | Why the module exists. Text on the same line or indented below. |
| `rules:` | A list of `- ` statements that must always be true. |
| `workflow: name` | `input:` (names), `steps:` (guidance, not checked), `failure:`, `recovery:`, `after:` (postconditions). |
| `example: name` | One observable case: `given:`, `when:`, `then:`. |
| `uncertainty: name` | `question:` and `blocking: yes` or `no`. |

A blocking uncertainty stops the module from being *ready*. To settle one,
write the answer as a rule or an example and remove the uncertainty.

## Detailed sections

```orin
module: demo.orders

purpose:
  Orders move from placed to paid.

type: sku

entity: order
  identity:
    id sku

state: placed

state: paid

capability: charge-order

capability: write-order-state

effect: persistent-entity-store.write.order-state
  requires:
    write-order-state
  durability: strong

workflow: pay
  actor: buyer
  input:
    buyer order
    order order
  output:
    order order
  requires:
    charge-order
  uses:
    persistent-entity-store.write.order-state
  actor-capabilities:
    buyer charge-order
    buyer write-order-state
  transitions:
    placed -> paid

rule: paid-is-final
  requires:
    paid
    charge-order
  claims:
    - A paid order does not go back to placed.

example: pay-once
  requires:
    pay
    paid-is-final
  then:
    order.state = paid
```

| Section | Lines inside |
|---|---|
| `type: name` | none. A simple value type, such as an id. |
| `entity: name` | `identity:` then `field type` lines. |
| `relation: name` | `between:` (two entities), `cardinality:` (`one-to-one`, `one-to-many`, `many-to-one`, `many-to-many`). |
| `state: name`, `capability: name` | none. |
| `effect: name` | `requires:` (capabilities), `durability:` (`strong` or `eventual`). |
| `workflow: name` | `actor:`, `input:` and `output:` (`name type` lines), `requires:`, `uses:`, `actor-capabilities:` (`actor capability` lines), `transitions:` (`from -> to`), `failure:`, `recovery:`, `after:`. |
| `rule: name` | `requires:` (names it talks about), `claims:` (`- ` statements). |
| `example: name` | `requires:` and `then:` (the expected result). |
| `uncertainty: name` | `blocking:` and `question:`. |

Ids are built as `<module>/<kind>/<name>`. Short names are turned into full
ids for you. A name that was never declared gives `ORIN-E007` or a type error.
A rule that says both "X" and "not X" gives `ORIN-E046`.

## Not supported yet

Outline style cannot yet write: plain entity fields, imports, `context`,
implementation policy, or uncertainty `options:`. See section 6 of `ORIN-SYNTAX-GRAMMAR.md`. Entity
lifecycle and effect inputs/outputs are also missing, so those items still block.

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
| E047 | Two rules say opposite things under the same condition (`when ...`). Python only for now. |
| E048 | An example expects what a rule it belongs to forbids. Python only for now. |
| E052 | A `type:` section has a bad line: bad `one of:` list, bad `number:` range, or an unknown line. Allowed lines: `one of: a, b`, `number: 0 to 100` (or `at least N`, `at most N`), `optional`. Python only for now. |
| E053 | A rule or example writes `name = value`, but the value is not in the `one of:` list of that type. Python only for now. |
| E054 | A rule or example writes `name = value`, but the value is not a number, or is outside the `number:` range. Python only for now. |
| E055 | A rule or example uses a missing value (`none`, `empty`) for a type that is not `optional`. Python only for now. |

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

Clear R020, R021, R050 and R040 in outline style:

```orin
rules:
  - A returned loan cannot be returned again.
    proved-by: double-return

workflow: return-book
  input:
    loan
  failure:
    The loan stays on loan and no fee is charged.
  recovery:
    The return may be repeated until it is recorded.
  after:
    The loan is returned.
```

`proved-by:` takes example names (comma separated; also allowed in a `rule:`
block). R001, R002, R010, R011, R030, R031, R032 still need the JSON form.

