---
name: wait-what
description: Use when the user signals confusion about your last message — "wait, what?", "I don't understand", "explain that simply", "you lost me", "in plain English". Re-pitches the unclear message in plain, jargon-free language instead of repeating it louder. Do NOT use for teaching a new topic from scratch (use teach-me) or for confusion about the codebase itself rather than about what you just said.
version: "2.0"
---

> Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock). See THIRD-PARTY-NOTICES.md.

# Wait, What?

That last message did not land. Don't repeat it, don't defend it, and
don't just add more words on top of the same explanation — re-pitch it.

## The re-pitch protocol

1. **Drop the jargon.** Identify every term in your last message that
   assumes prior context the user hasn't confirmed they have. Replace
   each one with plain language, or define it in the same breath you use
   it.
2. **Say it in one or two sentences first.** Give the plain-English
   headline before any detail. If you can't compress it to one sentence,
   you don't understand it well enough yet either — figure that out
   before re-explaining.
3. **Use concrete language over abstract language.** Prefer short,
   simple, unambiguous phrasing over compound or nested clauses. Say
   what happens, not what the mechanism theoretically enables.
4. **Match the project's own vocabulary.** If this codebase has an
   established domain-language document (e.g. `CONTEXT.md`) or a
   glossary, use its terms — don't introduce a synonym for something
   that already has a name here.
5. **Give a little context before the point.** A sentence of "here's
   where we are and why this matters" before the explanation itself
   orients better than diving straight back into detail.
6. **Check it landed.** End with a concrete way for the user to confirm
   understanding — a short example, a yes/no question, or "does that
   match what you were expecting?" — rather than assuming the re-pitch
   worked.

## What NOT to do

- Don't just repeat the same explanation louder or longer. If the first
  version didn't land, the fix is a different framing, not more of the
  same one.
- Don't get defensive about whether the original explanation was
  "technically correct." Correct-but-not-understood is a communication
  failure, not a user failure.
- Don't over-correct into a lecture. The goal is the smallest re-pitch
  that closes the gap, not a full tutorial — that's what `meta/teach-me`
  is for.
