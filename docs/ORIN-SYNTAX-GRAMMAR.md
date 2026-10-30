# Orin Outline Syntax Grammar

This is the exact grammar of **outline style**, the main way to write Orin
(see `DECISION-OUTLINE-SYNTAX.md`). It is written from the Python loader
(`implementations/python/orin_parser.py`) and the files in `examples/`. It
does not depend on any programming language. For a friendlier guide, see
`LANGUAGE-REFERENCE.md`.

Notation: `=` defines, `|` is "or", `[ ]` is optional, `{ }` is "zero or
more", `" "` is literal text. Names in `UPPER-CASE` are token classes.

## 1. Lexical rules

```ebnf
file        = { blank | comment | line } ;
blank       = whitespace-only line ;
comment     = [ whitespace ] "//" { any-char } ;
top-line    = no leading space or tab ,  KEY ":" [ whitespace ] [ VALUE ] ;
body-line   = leading space or tab , TEXT ;
KEY         = letter { letter | digit | "_" | "-" } ;
VALUE       = { any-char } ;            (* rest of the line, trimmed *)
TEXT        = { any-char } ;            (* the line, trimmed *)
```

- Blank lines and `//` comment lines are skipped everywhere.
- Indentation only separates levels: a line that starts with a space or tab
  belongs to the closest `top-line` above it. The amount of indentation does
  not matter.
- A line with no indent that is not `KEY: ...` is an error (`ORIN-P010`).
- Content before the first `top-line`, or a file whose first `top-line` is not
  `module:` with a value, is an error (`ORIN-P001`).

## 2. File structure

```ebnf
document = module-line , { section } ;
module-line = "module:" NAME ;
NAME     = non-space text ;             (* e.g. password-reset, shop.orders *)
section  = top-line , { body-line } ;
```

The loader picks a mode from the sections it finds:

- **Declaration mode**: used when the file has any of `type:`, `entity:`,
  `relation:`, `state:`, `capability:`, `effect:` or `rule:` (singular).
  Every section below turns into a typed object, and the file is fully checked.
- **Summary mode**: used otherwise (only `purpose:`, `rules:`, `workflow:`,
  `example:`, `uncertainty:`). Workflows and rules become simple objects with
  text only.

## 3. Sections

```ebnf
section = purpose | rules | workflow | example | uncertainty
        | type | entity | relation | state | capability | effect | rule ;

purpose = "purpose:" ( VALUE | NEWLINE { TEXT-LINE } ) ;
          (* inline text, or indented lines joined with spaces *)
```

Unknown top-level keys are read but ignored.

### 3.1 Summary-mode sections

```ebnf
rules       = "rules:" { "- " STATEMENT [ proved-by ] } ;
              (* each item becomes one rule named from its first 5 words *)
proved-by   = "proved-by:" EXAMPLE-NAME { "," EXAMPLE-NAME } ;
              (* indented line after the rule; sets its evidence links *)

workflow    = "workflow:" NAME { input-block | steps-block | failure
                               | recovery | after } ;
failure     = "failure:"  { TEXT } ;     (* failure behavior *)
recovery    = "recovery:" { TEXT } ;     (* recovery behavior *)
after       = "after:"    { TEXT } ;     (* postconditions: true once it finishes *)
input-block = "input:" ( { TEXT } ) ;        (* names only, one per line *)
steps-block = "steps:" { TEXT } ;            (* read as guidance; not checked *)

example     = "example:" NAME { given | when | then } ;
given       = "given:" { TEXT } ;
when        = "when:"  { TEXT } ;
then        = "then:"  { TEXT } ;

uncertainty = "uncertainty:" NAME { blocking | question | why | affects | option } ;
blocking    = "blocking:" ( "yes" | "no" | "true" | "false" ) ;
question    = "question:" { TEXT } ;
why         = "why:" { TEXT } ;                    (* or "why-it-matters:" *)
affects     = "affects:" NAME { "," NAME } ;       (* rule or workflow names; one per line also works *)
option      = "option:" { TEXT } { option-field } ;
option-field = ( "label:" | "explanation:" | "effects:" | "impact:" ) { TEXT } ;
```

An uncertainty is blocking only if `blocking:` is `yes` or `true`. A missing
`blocking:` means not blocking. Several lines under a label are joined with
spaces. The label may also hold its text on the same line.

`why:`, `affects:` and `option:` keep a decision inside the `.ori` file, so no
`.decisions.json` sidecar is needed. Each `option:` is one answer. Its text is
the label, and its id is made from the first words of the text. `affects:`
names are matched to rules and workflows. `inspect` and the agent show these
fields. If a structured fixture is borrowed for the file, it is used instead.

### 3.2 Declaration-mode sections

```ebnf
type        = "type:" NAME ;                       (* a value type *)
state       = "state:" NAME ;
capability  = "capability:" NAME ;

entity      = "entity:" NAME [ identity ] ;
identity    = "identity:" { FIELD } ;
FIELD       = FIELD-NAME TYPE-NAME ;               (* exactly two words *)

relation    = "relation:" NAME [ between ] [ cardinality ] ;
between     = "between:" { ENTITY-NAME } ;         (* exactly two *)
cardinality = "cardinality:" ( "one-to-one" | "one-to-many"
                             | "many-to-one" | "many-to-many" ) ;

effect      = "effect:" NAME [ requires ] [ durability ] ;
requires    = "requires:" { NAME } ;
durability  = "durability:" ( "strong" | "eventual" ) ;

workflow    = "workflow:" NAME { actor | input | output | requires | uses
                               | actor-caps | transitions | steps-block
                               | failure | recovery | after } ;
actor       = "actor:" ACTOR-NAME ;
input       = "input:"  { PARAM } ;
output      = "output:" { PARAM } ;
PARAM       = PARAM-NAME TYPE-NAME ;               (* exactly two words *)
uses        = "uses:" { EFFECT-NAME } ;
actor-caps  = "actor-capabilities:" { ACTOR-NAME CAPABILITY-NAME } ;
transitions = "transitions:" { STATE-NAME "->" STATE-NAME } ;

rule        = "rule:" NAME { requires | claims } ;
claims      = "claims:" { [ "- " ] STATEMENT } ;

example     = "example:" NAME { requires | then } ;
                       (* given/when lines are accepted but not used here *)

uncertainty = "uncertainty:" NAME { blocking | question } ;
```

Notes for declaration mode:

- Only these sub-labels are recognised inside a section: `identity`,
  `between`, `cardinality`, `requires`, `durability`, `actor`, `input`,
  `output`, `uses`, `actor-capabilities`, `transitions`, `claims`, `then`,
  `blocking`, `question`. Any other `label:` line is read as ordinary text of
  the sub-block above it.
- A line starting with `- ` has the dash removed.
- A name in `requires`, `between`, a `PARAM` type, `uses`, or a transition is
  looked up among the names declared in the file and turned into a full id
  (`<module>/<kind>/<name>`). A name that is not declared stays as written and
  the checker reports an unknown reference (`ORIN-E007`) or a type error.
- `FIELD` and `PARAM` lines that do not have exactly two words are dropped.
- Declaration mode reads `then:` of an example as its expected result.
  The singular `rule:` section uses `claims:`; the plural `rules:` list is
  summary mode only.

## 4. Object ids

Each section becomes an object with id `<module>/<kind>/<name>`. Kinds:
`type` → `value-type`, `entity` → `entity-type`; the others keep their name.
Two objects with the same id give `ORIN-E004`.

## 5. Complete small example

```orin
module: demo.shop

purpose:
  Sell items.

type: sku

entity: order
  identity:
    id sku

state: placed

state: paid

capability: charge-order

workflow: pay
  actor: buyer
  input:
    buyer order
    order order
  requires:
    charge-order
  actor-capabilities:
    buyer charge-order
  transitions:
    placed -> paid
```

## 6. Not yet supported

Outline style cannot yet express the following. Brace style (legacy) or the
JSON fixtures in `tests/conformance/` carry them today.

- Entity fields other than the `identity:` fields (no plain `field`).
- `context:` and implementation `policy` settings. (Imports now work; see
  below.)
- Rule ids chosen by the author in summary mode (ids come from the first five
  words of the text).
- Lifecycle, owner, scope, failure modes, data access and effect
  inputs/outputs (`ORIN-R001`–`R032`). A document that needs these stays
  `blocked` for them. Workflow `failure:`/`recovery:`/`after:` and rule
  `proved-by:` (`R020`, `R021`, `R050`, `R040`) are supported.
- Uncertainty `options:` and a recorded decision form. Today a decided
  question is answered by writing a rule or example and removing the
  uncertainty.
- Mixed modules: in a file with a singular `rule:` or other declarations,
  the plural `rules:` list and `steps:` are not turned into checked objects.
- Several blocking uncertainties in one summary-mode file currently produce a
  duplicate-id error (`ORIN-E004`, object `evidence/blocked`). This is a loader
  bug, not intended syntax.
- Package imports (only files next to the importing file are found).

### Imports

```text
imports:
  - ./shared-people.orin as people
  - finance.shared
```

Each item is a relative path or a module id (found in the same folder), with
an optional `as alias`. Without `as`, the alias is the last part of the module
name. Refer to imported things as `alias:name` or `alias:kind/name`, for
example `people:person` or `people:rule/no-self-decision`, in `requires`,
`uses`, field/input types and similar places. Errors: `ORIN-I001` missing
import, `ORIN-I002` cycle, `ORIN-I003` unreadable file, `ORIN-I004` alias used
twice, `ORIN-I005` unknown or ambiguous qualified name. A bare name without
a dot, path or `as` (such as `account-store`) that matches no file stays an
external contract and is not an error.
