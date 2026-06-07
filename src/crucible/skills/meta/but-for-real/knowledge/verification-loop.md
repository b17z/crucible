---
name: Verification Loop
description: The concrete skeptical-pass checklist, with real examples of Crucible v2 work that was declared "done" and wasn't.
triggers: [verification, proof, done, skeptical, edge-case]
type: principle
---

# Verification Loop

A skeptical pass is not vibes. It is a checklist, and it produces evidence.

## The checklist

For each "done" claim, before you make it:

- [ ] **Diff read.** Open the actual diff. Does every change do what you think it does? Is anything in there you didn't mean to ship?
- [ ] **Real-environment run.** Run the artifact the way it runs in production. Right interpreter, right env, right inputs.
- [ ] **Empty / missing / malformed cases.** Empty array. Missing tool. Malformed input file. Absent config. These are where "works on the happy path" dies.
- [ ] **Adversarial input.** What does a hostile or careless input do? Injection, traversal, oversized, wrong-type.
- [ ] **Full suite, not the subset.** Run everything. If you exclude anything, name what and why, and confirm the exclusion is legitimate (env-broken) not convenient (it was failing).
- [ ] **Claim → evidence.** Every assertion in your "done" message is backed by a command and its output.
- [ ] **Coverage gaps stated.** What did you NOT verify? Say so.

## Real incidents from Crucible v2 (why this skill exists)

These are actual cases where work was declared done in this codebase and
the skeptical pass found it wasn't. Each one is a lesson encoded.

### Incident 1 — "667/669 tests pass"

The claim excluded the integration suite every time via
`--ignore=tests/test_integration.py`. The real number was 660/669 —
five slither tests were also failing, never looked at. **Lesson:** "X/Y
passing" where Y is a convenient subset is not Y passing. Run the whole
thing once, then justify any exclusion.

### Incident 2 — magic_comments YAML injection

The `crucible-approve:` parser captured any non-whitespace as the
package name and wrote it straight into a YAML file. A trailing colon
in the input produced malformed YAML that crashed any downstream
parser. **Lesson:** untrusted text that becomes structured data must be
validated against a strict charset before it's written. The happy-path
test (`lodash@4.17.21`) passed; the adversarial input (`foo@1.0:`)
broke it.

### Incident 3 — npm_install_gate awk parser

The gate parsed approved-deps.yaml with awk, which accepted files that
strict YAML parsers reject (`name:"x"` with no space). The gate would
approve a package no Python tool could read. **Lesson:** when two
consumers parse the same file, they must use the same parser. Test the
malformed-file case explicitly — and make it fail closed.

### Incident 4 — the wheel didn't ship the work

Phase 1b and Phase 2 added hooks, policies, and a whole reorganized
skills tree at the repo root — outside the package. The wheel
package-data globs didn't include them. A `pip install` of the wheel
got **none** of it. The claim "Phase 1b/2 done" was true for a
dev checkout and false for every wheel user. **Lesson:** "done"
includes "ships". Build the artifact (`python -m build`), open it
(`unzip -l`), and confirm your files are actually inside.

### Incident 5 — mapfile under bash 3.2

The magic_comments hook used `mapfile` (bash 4+) and `"${arr[@]}"`
under `set -u` (errors on empty arrays in bash 3.2). The shebang is
`#!/bin/bash`, which on macOS — the author's own machine — is bash
3.2. The hook was **broken on the author's primary platform**. The
tests passed only because they invoked the hook via `bash` (Homebrew
5.x on PATH) instead of `/bin/bash`. **Lesson:** test the artifact
under the interpreter its shebang actually resolves to. A test that
uses a different interpreter than production is testing the wrong
thing.

## The meta-lesson

In every one of these, the work *looked* done. The code was written,
the obvious case worked, the change felt complete. "Done" was a feeling,
not a proof. The skeptical pass turns the feeling into either evidence
or a bug report — and it is always one of the two.

When you catch yourself about to say "ready for the next phase," stop
and run the loop. The five minutes you spend is cheaper than the
"can you try again?" that's coming otherwise.
