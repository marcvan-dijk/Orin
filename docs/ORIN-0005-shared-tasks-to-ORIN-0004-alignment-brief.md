# ORIN-0005 Shared-Tasks ↔ ORIN-0004 Alignment Brief (Item 41)

**Status:** Docs-only post-MVP alignment brief  
**Scope boundary:** No implementation/runtime changes

## Purpose

Map the first ORIN-0005 shared-tasks semantic additions onto existing ORIN-0004
declaration kinds so post-MVP execution can stay meaning-first and avoid
accidentally coupling semantics to host/runtime choices.

## Mapping: ORIN-0005 additions to ORIN-0004 declaration kinds

| ORIN-0005 semantic addition | ORIN-0004 declaration kinds involved | Semantic requirement (language meaning) | Host/runtime choices (non-semantic) |
| --- | --- | --- | --- |
| Entity schema with identity + typed fields | `entity-type`, `value-type`, `rule` | Stable entity identity, typed field constraints, required/optional and mutability constraints where observable | Storage shape, ORM/class layout, serialization details |
| Relationship cardinality + ownership | `relation`, `entity-type`, `rule` | Declared endpoints, ownership, and cardinality constraints that drive validity and authorization | Join tables, indexes, FK implementation strategy |
| Explicit transition contract | `workflow`, `state`, `rule` | Allowed transitions, guards, and failure behavior (for example terminal completion) | Locking model, transaction mechanism, retry technique |
| Typed workflow I/O + failure contract | `workflow`, `value-type`, `rule`, `effect` | Named typed inputs, output contract, stable failure identities and validation semantics | Transport protocol, status code mapping, wire format |
| Actor-bound authorization context | `workflow`, `capability`, `relation`, `rule`, `entity-type` | Invocation actor identity and authorization evaluation against actor/object relationships | Auth tokens/sessions, middleware, role service implementation |
| Persistence durability/read-write boundary | `effect`, `entity-type`, `relation`, `workflow` | Which changes must persist across invocations and which effects represent reads/writes | Database product, file store, managed service, caching strategy |

## Decomposition summary

- ORIN-0005 does **not** require new top-level language concepts such as
  `database`, `API`, `role`, or `UI`.
- The first shared-tasks semantic step is mostly completion/refinement of
  ORIN-0004 kinds already declared (`entity-type`, `relation`, `workflow`,
  `state`, `capability`, `effect`, `rule`).
- Any behavioral requirement must be represented as semantic claims; runtime
  and lowering decisions remain implementation policy.

## Scope guard for next increment

- This brief is alignment only.
- Do not start shared-tasks implementation from this document alone.
- Activate any post-MVP execution work through `ORIN-0003` first.
