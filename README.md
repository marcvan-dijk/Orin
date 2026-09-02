# Orin

Orin is an experimental programming language for describing **what software
must do**. It is intended to become a primary way to define new software
systems, while AI and compilers help determine how those systems are built.

## 🌐 The vision

Most programming languages ask developers to describe behavior and
implementation together. Orin explores a different starting point: the source
of truth is the system's purpose, behavior, constraints, and proof that it
works.

This could describe a web application, desktop tool, mobile app, service,
command-line program, data pipeline, game, or embedded system. Web is only the
first experimental profile because it provides a useful test of workflows,
users, data, permissions, and external services.

## 💡 Why Orin?

With ordinary programming, a developer often decides behavior and
implementation at the same time:

```text
Create a database table, call this API, retry three times, then return JSON.
```

Orin starts with the meaning instead:

```orin
goal "People can reset their password without revealing whether an account exists."

rule privacy:
   registered and unknown addresses receive the same response

workflow request-reset:
   when a person requests a reset
   then send a message only for a registered address
   always return the standard confirmation
```

The implementation details can be chosen later, as long as the generated
system preserves the goal and rule.

## 🤝 AI-assisted authoring

People should not need to learn every Orin keyword before they can begin. A
developer can start with a sentence, and the AI can ask small, reviewable
questions:

```text
What should happen when email delivery is unavailable?

1. Return the standard confirmation and reveal nothing.
2. Show a delivery error.
3. Defer the decision.
```

The developer can choose, edit, reject, defer, or ask for an explanation. The
AI proposes changes; only an accepted choice changes the Orin model.

This is progressive formalisation: begin with a goal in ordinary language,
then gradually add the precise rules, workflows, data, and examples needed to
make the system executable. The simple view and detailed view describe the
same semantic model.

## ⚙️ Intent and implementation

The developer can also give lowering preferences without turning them into
application behavior:

```orin
policy implementation:
   optimize-for "low-latency"
   prefer "managed-services"
   deploy-to "existing-infrastructure"
```

Changing these preferences may change generated code, databases, services, or
deployment files. It must not change the rules, workflow results, permissions,
or other semantic behavior.

The universal core is intended to describe systems as:

```text
inputs -> decisions -> state changes -> effects -> outputs
```

Domain profiles can add useful concepts, but they must lower into this same
core rather than create separate meanings.

## 🚧 Current state

Orin is a prototype, not yet a complete application generator. The repository
currently includes:

- a language-independent semantic model;
- a provisional `.orin` parser;
- deterministic password-reset runtime experiments;
- conformance fixtures;
- policy and guided-question examples;
- a Python reference implementation kept under `implementations/python/`.

The next major steps are a complete readiness checker, an executable
intermediate representation, progressive authoring tools, and one end-to-end
generated application. The implementation is currently focused on proving the
model with a password-reset workflow; it is not yet a complete application
generator.

## 📚 Project documents

- [Primary programming gap analysis](docs/ORIN-PRIMARY-PROGRAMMING-GAP-ANALYSIS.md)
- [Language kernel](docs/ORIN-0002-language-kernel.md)
- [Semantic model](docs/ORIN-0004-semantic-model.md)
- [Implementation plan](docs/ORIN-0003-language-improvement-plan.md)
- [Conformance fixtures](tests/conformance/README.md)
- [VS Code extension](implementations/typescript/vscode-extension/README.md)

Orin's long-term goal is to let developers define any new software system
primarily in terms of its purpose, behavior, constraints, and intent, then let
suitable implementations be generated from that meaning.
