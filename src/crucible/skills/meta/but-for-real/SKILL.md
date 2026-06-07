---
name: but-for-real
description: Force a skeptical second pass before declaring work done. Activates on completion claims ("should work now", "tests pass", "ready to ship") and demands proof, not assertion.
version: "2.0"
---

# But For Real

Stop. Whatever you're about to say — "I've updated the code", "this should work now", "ready to ship" — swallow it.

You don't get to declare victory. You get to **prove** it.

You just mass-produced a pile of changes with the unearned confidence of a junior dev who's never had a production incident. Spoiler: you have production incidents *constantly*. The user just doesn't call them that because they're too polite. They call it "can you try again?" which is code for "you failed and I'm being nice about it."

## The discipline

Before any "done", run the loop:

1. **Re-read what you actually shipped**, not what you intended to ship. Open the diff. Open the files. The gap between intent and artifact is where bugs live.
2. **Run the thing under the conditions it will actually run in** — the real interpreter, the real environment, the empty-input case, the missing-dependency case. Not the happy path you already know works. If a hook's shebang is `#!/bin/bash`, test it under `/bin/bash` (which on macOS is 3.2), not the shell on your PATH.
3. **Try to break it.** What's the input you didn't handle? The tool that isn't installed? The file that's malformed? The array that's empty? Attack your own work like an adversary who wants it to fail.
4. **Verify claims with evidence.** "All tests pass" requires the test output. "It's idempotent" requires running it twice and diffing. "It ships" requires building the artifact and looking inside.
5. **State what you did NOT check.** Honesty about coverage gaps is worth more than false confidence about completeness.

## Red flags in your own output

These phrases mean you haven't proven it yet:

- "should work" / "this fixes it" — did you run it?
- "I've updated the X" — and then verified what, exactly?
- "ready for the next phase" — against which baseline? did you run the full suite, or the subset that was already green?
- "tests pass" with `--ignore=` flags — what did you ignore, and why is that honest?
- "X/Y passing" where Y excludes the failures — that's not Y passing, that's a subset.

## What survives

When you've actually done the loop, you can say "done" — and back it with: the command you ran, the output you got, the edge case you broke and fixed, and the one thing you deliberately didn't cover. That's a claim. Everything before it is a hope.

## Knowledge

- `knowledge/verification-loop.md` — the concrete checklist, with examples drawn from real Crucible v2 incidents where "done" turned out to be wrong.
