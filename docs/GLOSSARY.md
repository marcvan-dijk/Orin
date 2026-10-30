# Orin glossary: 10 words in simple English

1. **Orin program**: a plain text file that says what software must do. It
   does not say how to build it. Example: `examples/password-reset.orin`.
2. **Semantic**: about *meaning*. "Semantic model" means the meaning of the
   program, written in a form a tool can read (a `.json` file).
3. **Canonical**: the one official version. "Canonical meaning" is the one
   agreed meaning. Different implementations can look different, but the
   canonical meaning stays the same.
4. **Intent**: what the program is for and what must always be true
   (`purpose` and `rules`).
5. **Uncertainty**: an open question that nobody has answered yet. In the
   tools it is also called "blocking": Orin will not build the program until a
   person answers it.
6. **Decision**: the human answer to an uncertainty. It is chosen from clear
   options and then recorded.
7. **Evidence**: something you can check to see that the intent is kept, such
   as an `example` or a test.
8. **Implementation**: the code that makes the program work. It can change
   without changing the Orin program.
9. **Readiness**: a check that tells you if the program is complete enough to
   build. Codes such as `ORIN-R001` name what is missing (see
   [`ONBOARDING.md`](./ONBOARDING.md#what-the-readiness-codes-mean)).
10. **Outline style**: the standard way to write Orin: short keywords, then an
    indented list. See [`ORIN-SYNTAX-GUIDE.md`](./ORIN-SYNTAX-GUIDE.md).

Back to [`../README.md`](../README.md).
