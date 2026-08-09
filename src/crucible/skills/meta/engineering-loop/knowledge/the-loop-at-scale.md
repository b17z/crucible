---
name: The Loop at Scale
description: The same six-step discipline once agents do the building — a controller that coordinates instead of coding, fresh-context workers, an independent reviewer, and a recovery ledger. Distilled from the project's own multi-agent field notes.
triggers: [multi-agent, controller, subagent, fix loop, review, ledger]
type: principle
---

# The Loop at Scale

Everything in this skill — say it plainly, think small, write it down,
build the smallest thing, prove it honestly, keep what you learned —
still holds once the "builder" is no longer a single person typing
code. This is where the loop grows up to: a controller coordinating
multiple agents, each doing one piece, none of them trusted until
they've been checked.

## The big idea: the controller never builds

In a multi-agent setup, one agent plays controller. Its job is to keep
the plan, hand out work, and make judgment calls — not to write
implementation code itself. Each task goes to a separate, fresh worker
agent that starts with zero conversation history: exactly the context
it needs for its one task, and nothing else. A second, independent
agent then reviews what the first one built. Nothing is trusted until
it has been attacked.

Two reasons this beats one agent doing everything end to end:

1. **Fresh context avoids contamination.** A worker that inherited the
   whole conversation carries its earlier assumptions and mistakes
   forward. A worker that only knows its own task reasons cleanly about
   just that task — and, because it isn't invested in the plan, it will
   sometimes disagree with it. That disagreement is useful: workers
   with fresh eyes have caught plans that double-counted costs or
   carried forward rules that no longer applied.
2. **The author can't grade their own homework.** The agent (or person)
   who wrote the code is the worst-positioned to spot its own bug — it
   already believes its own reasoning. A separate reviewer, working
   from a different prompt and a different context, catches what the
   builder was blind to.

## The per-task loop

Each unit of work follows the same shape:

1. **A task brief** — just the one task, not the whole plan.
2. **Record the starting point** — note what state things are in before
   the work starts, so progress is checkable afterward.
3. **Dispatch a fresh implementer** — new context, no history. It
   builds test-first, commits its work, reviews itself once, and
   reports what it did.
4. **Package the result as a review artifact** — the diff, handed over
   as a file, not pasted into anyone's conversation.
5. **Dispatch an independent reviewer** — a different agent, checking
   both "does this match what was asked" and "is this code actually
   good."
6. **Branch on the verdict** — clean review means the task is complete.
   Any findings open a fix loop.

## The fix loop

Findings go back, word for word, to the *same* implementer that did the
original work — its context is still intact, and it already knows the
code. It fixes what was flagged, re-runs its checks, and adds to its
report. A second, scoped review then looks at only the fix — not the
whole task again — and gives each finding a verdict: addressed, or not
addressed, plus a flag for any new problem the fix itself introduced.

This can repeat, but not forever. After a few rounds with the same
implementer and no resolution, the task escalates to a fresh, more
capable implementer — the reasoning is that if an agent has tried and
failed several times, the problem may be something it structurally
can't see about its own work, so the fix needs both new eyes and more
capability, not another attempt from the same place. If the loop is
still open after its maximum number of rounds, a breaker trips: the
controller itself adjudicates each remaining finding — deciding to
accept it as a known, recorded limitation, or stopping the whole
process to bring a person in. Either way, it's a deliberate decision,
not an infinite retry.

## The load-bearing habits

A few rules make the whole thing work, and they're easy to violate
without noticing:

- **Artifacts live as files, never pasted into the controller's own
  context.** Task briefs, worker reports, diffs — all handed over by
  file path. Pasting a large diff directly into a conversation means it
  sits there taking up space forever, and the controller's judgment
  slowly gets worse the fuller its context gets.
- **A ledger tracks progress outside anyone's memory.** A plain record
  of which tasks are done, in progress, or blocked, alongside the git
  commits that prove it — because conversation memory does not survive
  a context reset, but a file on disk and a git log do. It's the
  equivalent of a flight recorder: if everything else is lost, the
  ledger and the commit history are enough to figure out exactly where
  things stood and pick back up without redoing finished work.
- **Never pre-judge for the reviewer.** Telling a reviewer "this part
  is fine, don't bother checking it" defeats the entire point of having
  a second, independent opinion. Let it raise whatever it finds; decide
  afterward whether the finding matters.
- **Never let the controller fix things directly.** The moment the
  coordinator starts patching code itself, the fix skips review
  entirely and the controller's own context fills up with
  implementation detail it doesn't need. A problem found during review
  always goes back to an implementer, never straight to a controller
  edit.

## The payoff

This is slower than one agent writing code start to finish and calling
it done. That slowness is deliberate, and it's spent in exactly the
right place: independent review — real review, not a rubber stamp —
regularly finds bugs, and reproduces them through the actual code path,
that a single-pass build would have shipped looking completely fine.
That's the dangerous kind of wrong: not a crash, but quietly incorrect
behavior that erodes trust the moment someone notices the numbers don't
add up. A single implementer, confident and unchecked, would have
called it done. The loop is slow exactly where being slow prevents
that.

The six steps at the top of this skill are the same discipline, scaled
down to one person and one sitting: say it plainly instead of skipping
straight to jargon, think small instead of designing the whole system
at once, write down what "done" means before starting, build only the
next small piece, prove it instead of assuming it, and keep the lesson
instead of losing it. Multi-agent coordination is what that discipline
looks like once there's more than one pair of hands — and more than one
set of eyes — doing the work.
