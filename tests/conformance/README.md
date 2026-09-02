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

Future host-language runners belong in a separate directory named for the host
language. They must consume these fixtures rather than redefine their contents.
