---
name: systematic-debugging
description: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes. Enforces root-cause investigation through four phases (root cause, pattern analysis, hypothesis testing, implementation) instead of guess-and-check. Do NOT use for feature design (use brainstorming) or for changes with no observed failure — this skill activates on something being broken, not on building something new.
version: "2.0"
---

> Adapted from obra/superpowers (MIT, © 2025 Jesse Vincent). See THIRD-PARTY-NOTICES.md.

# Systematic Debugging

## Overview

**Core principle:** ALWAYS find root cause before attempting fixes.
Symptom fixes are failure.

**Violating the letter of this process is violating the spirit of
debugging.**

## The iron law

```
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

If you haven't completed Phase 1, you cannot propose fixes.

## When to use

Use for ANY technical issue:

- Test failures
- Bugs in production
- Unexpected behavior
- Performance problems
- Build failures
- Integration issues

**Use this ESPECIALLY when:**

- Under time pressure (emergencies make guessing tempting)
- "Just one quick fix" seems obvious
- You've already tried multiple fixes
- Previous fix didn't work
- You don't fully understand the issue

**Don't skip when:**

- Issue seems simple (simple bugs have root causes too)
- You're in a hurry (rushing guarantees rework)
- Someone wants it fixed NOW (systematic is faster than thrashing)

## The four phases

You MUST complete each phase before proceeding to the next.

### Phase 1: Root cause investigation

**BEFORE attempting ANY fix:**

1. **Read error messages carefully**
   - Don't skip past errors or warnings.
   - They often contain the exact solution.
   - Read stack traces completely.
   - Note line numbers, file paths, error codes.

2. **Reproduce consistently**
   - Can you trigger it reliably?
   - What are the exact steps?
   - Does it happen every time?
   - If not reproducible → gather more data, don't guess.

3. **Check recent changes**
   - What changed that could cause this?
   - Git diff, recent commits.
   - New dependencies, config changes.
   - Environmental differences.

4. **Gather evidence in multi-component systems**

   **WHEN the system has multiple components (CI → build → signing,
   API → service → database):**

   **BEFORE proposing fixes, add diagnostic instrumentation:**

   ```
   For EACH component boundary:
     - Log what data enters the component
     - Log what data exits the component
     - Verify environment/config propagation
     - Check state at each layer

   Run once to gather evidence showing WHERE it breaks
   THEN analyze evidence to identify the failing component
   THEN investigate that specific component
   ```

   **Example (multi-layer system):**

   ```bash
   # Layer 1: Workflow
   echo "=== Secrets available in workflow: ==="
   echo "IDENTITY: ${IDENTITY:+SET}${IDENTITY:-UNSET}"

   # Layer 2: Build script
   echo "=== Env vars in build script: ==="
   env | grep IDENTITY || echo "IDENTITY not in environment"

   # Layer 3: Signing script
   echo "=== Keychain state: ==="
   security list-keychains
   security find-identity -v

   # Layer 4: Actual signing
   codesign --sign "$IDENTITY" --verbose=4 "$APP"
   ```

   **This reveals:** which layer fails (secrets → workflow OK,
   workflow → build broken).

5. **Trace data flow**

   **WHEN the error is deep in the call stack:**

   - Where does the bad value originate?
   - What called this with the bad value?
   - Keep tracing up until you find the source.
   - Fix at the source, not at the symptom.

### Phase 2: Pattern analysis

**Find the pattern before fixing:**

1. **Find working examples**
   - Locate similar working code in the same codebase.
   - What works that's similar to what's broken?

2. **Compare against references**
   - If implementing a pattern, read the reference implementation
     COMPLETELY.
   - Don't skim — read every line.
   - Understand the pattern fully before applying it.

3. **Identify differences**
   - What's different between working and broken?
   - List every difference, however small.
   - Don't assume "that can't matter."

4. **Understand dependencies**
   - What other components does this need?
   - What settings, config, environment?
   - What assumptions does it make?

### Phase 3: Hypothesis and testing

**Scientific method:**

1. **Form a single hypothesis**
   - State clearly: "I think X is the root cause because Y."
   - Write it down.
   - Be specific, not vague.

2. **Test minimally**
   - Make the SMALLEST possible change to test the hypothesis.
   - One variable at a time.
   - Don't fix multiple things at once.

3. **Verify before continuing**
   - Did it work? Yes → Phase 4.
   - Didn't work? Form a NEW hypothesis.
   - DON'T add more fixes on top.

4. **When you don't know**
   - Say "I don't understand X."
   - Don't pretend to know.
   - Ask for help.
   - Research more.

### Phase 4: Implementation

**Fix the root cause, not the symptom:**

1. **Create a failing test case**
   - Simplest possible reproduction.
   - Automated test if possible.
   - One-off test script if no framework.
   - MUST have before fixing.

2. **Implement a single fix**
   - Address the root cause identified.
   - ONE change at a time.
   - No "while I'm here" improvements.
   - No bundled refactoring.

3. **Verify the fix**
   - Test passes now?
   - No other tests broken?
   - Issue actually resolved?
   - Run the full verification loop before claiming success — command
     run, output seen, not "should be fixed."

4. **If the fix doesn't work**
   - STOP.
   - Count: how many fixes have you tried?
   - If < 3: return to Phase 1, re-analyze with new information.
   - **If ≥ 3: STOP and question the architecture (step 5 below).**
   - Don't attempt fix #4 without an architectural discussion.

5. **If 3+ fixes failed: question architecture**

   **Pattern indicating an architectural problem:**
   - Each fix reveals new shared state/coupling/problem in a different
     place.
   - Fixes require "massive refactoring" to implement.
   - Each fix creates new symptoms elsewhere.

   **STOP and question fundamentals:**
   - Is this pattern fundamentally sound?
   - Are we sticking with it through sheer inertia?
   - Should we refactor architecture vs. continue fixing symptoms?

   **Discuss with the user before attempting more fixes.**

   This is NOT a failed hypothesis — this is a wrong architecture.

## Red flags — stop and follow process

If you catch yourself thinking:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Add multiple changes, run tests"
- "Skip the test, I'll manually verify"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "Here are the main problems: [lists fixes without investigation]"
- Proposing solutions before tracing data flow
- **"One more fix attempt" (when already tried 2+)**
- **Each fix reveals a new problem in a different place**

**ALL of these mean: STOP. Return to Phase 1.**

**If 3+ fixes failed:** question the architecture (see Phase 4, step 5).

## Signals you're doing it wrong

Watch for these redirections from the user:

- "Is that not happening?" — you assumed without verifying.
- "Will it show us...?" — you should have added evidence gathering.
- "Stop guessing" — you're proposing fixes without understanding.
- "Think harder about this" — question fundamentals, not just symptoms.
- "We're stuck?" (frustrated) — your approach isn't working.

**When you see these:** STOP. Return to Phase 1.

## Common rationalizations

| Excuse | Reality |
|--------|---------|
| "Issue is simple, don't need process" | Simple issues have root causes too. Process is fast for simple bugs. |
| "Emergency, no time for process" | Systematic debugging is FASTER than guess-and-check thrashing. |
| "Just try this first, then investigate" | First fix sets the pattern. Do it right from the start. |
| "I'll write test after confirming fix works" | Untested fixes don't stick. Test first proves it. |
| "Multiple fixes at once saves time" | Can't isolate what worked. Causes new bugs. |
| "Reference too long, I'll adapt the pattern" | Partial understanding guarantees bugs. Read it completely. |
| "I see the problem, let me fix it" | Seeing symptoms is not understanding root cause. |
| "One more fix attempt" (after 2+ failures) | 3+ failures = architectural problem. Question the pattern, don't fix again. |

## Quick reference

| Phase | Key activities | Success criteria |
|-------|---------------|------------------|
| **1. Root cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
| **2. Pattern** | Find working examples, compare | Identify differences |
| **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
| **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

## When process reveals "no root cause"

If systematic investigation reveals the issue is truly environmental,
timing-dependent, or external:

1. You've completed the process.
2. Document what you investigated.
3. Implement appropriate handling (retry, timeout, error message).
4. Add monitoring/logging for future investigation.

**But:** 95% of "no root cause" cases are incomplete investigation.
