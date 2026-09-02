# Orin Conformance Fixtures

This directory contains language-neutral data fixtures for Orin implementations.
The files are not tied to a parser, runtime, programming language, or target.

A conforming implementation should be able to:

1. Load `password-reset.model.json` as a semantic model.
2. Report its compilation status as `blocked` because `rate-limit` is unresolved.
3. Evaluate the cases in `password-reset.cases.json`.
4. Preserve object identities and references.
5. Produce equivalent canonical output when the same model is loaded through
   another frontend.

`password-reset.policies.json` adds two lowering-policy variants. A conforming
implementation should preserve equal semantic behavior for both variants while
allowing their target artifact strategies to differ. Policy data guides
lowering; it is not part of canonical semantic equality.

`authoring-choices.json` defines a language-neutral guided question. Its
options are reviewable proposals, not implicit decisions; accepting one must
update the same semantic model used by direct authoring, while deferring keeps
the affected behavior unresolved.

`password-reset.cases.json` is executable specification data. The reference
runner generates one test scenario per case, including failure and concurrent
requests, so adding a case extends conformance coverage without duplicating
the expected behavior in host-language test code.

Future host-language runners belong in a separate directory named for the host
language. They must consume these fixtures rather than redefine their contents.
