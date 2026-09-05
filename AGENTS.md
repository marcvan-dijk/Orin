# AGENTS.md — Working on Orin

## What Orin is

Orin is an experiment in a different way of programming software.

The central question is:

> If AI increasingly writes the implementation, what should humans program?

Orin explores the idea that humans should primarily define **what software should do**, while AI and implementations handle more of **how it is built**.

The goal is not to replace programming with prompts.

The goal is to create a durable, human-understandable representation of a program that remains the source of truth even when implementations change.

---

# Core architecture

Keep these concerns separate:

```text
AUTHORING
How a human or AI expresses a program
        ↓
SEMANTICS
What the program means
        ↓
IMPLEMENTATION
How that meaning is realised or executed
        ↓
VERIFICATION
Does the implementation satisfy the accepted meaning?