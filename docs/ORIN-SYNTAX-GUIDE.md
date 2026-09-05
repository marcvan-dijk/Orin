# Orin Syntax Guide

This guide describes the current readable outline style for Orin authoring.

## Core idea

An Orin document is a structured outline made of:

- labels
- indented content
- optional lists

The goal is to keep Orin readable to humans while still being precise enough for tooling and semantic analysis.

## Basic rules

### 1. Section labels

A section starts with a label followed by `:`.

Examples:

```text
module: password-reset
purpose:
```

A label may also appear with a short inline value:

```text
module: password-reset
```

### 2. Indentation

Indented lines belong to the section above them.

Example:

```text
purpose:
  Reset passwords safely.
```

### 3. Lists

Lists use `-`.

Example:

```text
rules:
  - Do not reveal whether an email exists.
  - Reset links expire after 15 minutes.
```

### 4. Nested sections

Sections may contain nested sections.

Example:

```text
workflow: request-reset
  input:
    email
  steps:
    check account
    return same response
```

### 5. Plain text values

Values are plain text unless a tool or compiler interprets them as structured meaning.

Example:

```text
question:
  Should reset requests be rate-limited?
```

## Suggested section order

For readability, prefer this order:

1. `module`
2. `purpose`
3. `rules`
4. `workflow`
5. `examples`
6. `uncertainty`
7. `targets`

## Beginner-friendly example

```text
module: password-reset

purpose:
  Reset passwords safely.

rules:
  - Do not reveal whether an email exists.
  - Reset links expire after 15 minutes.
  - Reset links can only be used once.

workflow: request-reset
  input:
    email
  steps:
    check account
    create token if allowed
    send reset message if allowed
    return same response

uncertainty:
  rate-limit
  blocking: yes
  question:
    Should reset requests be rate-limited?
```

## Notes

- Keep the syntax light and readable.
- Prefer short section names.
- Keep the meaning explicit in prose.
- Avoid making the format look like general-purpose YAML serialization.
