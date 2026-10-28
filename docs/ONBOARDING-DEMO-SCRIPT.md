# Onboarding demo video script (about 3 minutes)

Follows [`ONBOARDING.md`](./ONBOARDING.md). Use a large terminal font. Speak
slowly and use short sentences.

| Time | Screen | Narration |
| --- | --- | --- |
| 0:00 | Title: "Orin: write what software must do" | "If AI writes the code, what should people write? Orin says: the meaning of the program." |
| 0:20 | Open `examples/password-reset.orin` | "This is a password reset. Here is the purpose. Here are the rules. Here are two examples. And here is one open question: rate limit." |
| 0:50 | Show the table of intent, decision, evidence | "Three ideas. Intent: what must be true. Decision: a choice a human must make. Evidence: a check that the intent is kept." |
| 1:10 | Run `python -m tooling.python.orin_agent inspect examples/password-reset.orin` | "The agent says: blocked. It lists the decision, the options, and the parts it touches: the workflow and both examples. It does not guess." |
| 1:40 | Run `decide ... --option five-per-15m-per-address-and-origin --write out/five.json` | "I choose five requests per 15 minutes. The decision is accepted. The program is now ready." |
| 2:00 | Run the second `decide` with `three-per-hour-per-address`, then `diff out/five.json out/three.json` | "I change my mind. Only one rule line changes. The examples stay true." |
| 2:25 | Run `python implementations/python/password_reset_proof.py` | "The same meaning gives two different implementation plans. The meaning does not change." |
| 2:45 | Run the TypeScript test, show `# pass 4` | "Evidence checks the implementation. Code can change. Intent, decisions and evidence stay." |
| 2:55 | End card: `docs/ONBOARDING.md` | "Try the 10-minute walkthrough." |

Before recording: run `mkdir -p out`. After: delete `out/`.
