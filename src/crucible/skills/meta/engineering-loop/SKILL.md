---
name: engineering-loop
description: Use when someone has never shipped software before and wants to build their first thing — "I'm new", "first project", "where do I start", "help me build my first app/site/tool" — plus user-invocable any time someone wants the beginner-friendly build cycle explained. Walks through six plain-language steps from idea to a proven, remembered result, each step naming the Crucible skill that carries it. Do NOT use for someone who already knows how to code and just wants a specific skill (route them to that skill directly) or for an experienced engineer's normal feature work (that's the skills below, used directly, not this beginner wrapper).
version: "1.0"
---

# The Engineering Loop

You've never shipped software before, or you're not sure how the pieces
fit together. Good news: it's six steps, on repeat, every time. This
skill is the map. Each step has its own Crucible skill that does the
real work — this one just tells you which one to reach for and when.

See `docs/LOOP.md` in the crucible repo
(https://github.com/b17z/crucible/blob/main/docs/LOOP.md) for a full
worked example (a page that shows a running club's next meetup, walked
through all six steps).

## The six steps

### 1. Say it plainly

Before anything else, say what you want in one sentence a friend would
understand — no jargon, no tool names. "A page that shows when my
running club meets next." If you can't say it in one sentence, you
don't know what you're building yet — keep talking it through until you
can.

If your own explanation (or the agent's) doesn't make sense, this is
also where you catch that mid-conversation: ask "wait, what?" or "can
you explain that simply?" and the **`meta/wait-what`** skill re-explains
in plain language instead of repeating the same words louder. Activate
it any time by just saying you're confused. Skills have a folder-style
full name like `meta/wait-what` — always use the full name with the
discover command: `crucible skills discover meta/wait-what` shows you
what it does.

### 2. Think small first

Don't design the whole dream. Find the smallest version that could
possibly work, and think about what could go wrong with it. A running
club page doesn't need logins, a database, or a mobile app on day one —
it needs one page with one date on it.

This is **`meta/brainstorming`**: one question at a time, a couple of
options with trade-offs, and a short plan you approve before any code
gets written. Nothing gets built until you've seen the plan and said
yes. Run `crucible skills discover meta/brainstorming` to see it, or
just say "let's build X" and it activates.

### 3. Write it down

Three to five sentences describing what you're making is a spec. Not a
formal document — just enough that you and the agent building it agree
on what "done" looks like before work starts. "A single web page. It
shows the next meetup's date, time, and location. It updates when I
edit one text file. No login, no database."

**`meta/spec-validator`** is the check that makes sure this step
actually happens before code gets written — it's why the agent asks
"is there a spec for this?" instead of just diving in. `crucible skills
discover meta/spec-validator` explains the gate and how to skip it
deliberately for a quick experiment (see "when to break the loop"
below).

### 4. Build the smallest thing

Now, and only now, write code — and only the one small step from step
2, not the whole dream. Resist the urge to also add the login screen,
the database, and the mobile app while you're in there. One step at a
time keeps mistakes small and easy to spot.

**`meta/coding-discipline`** is the set of habits that keeps this step
honest: minimum code that solves the problem, changes that trace back
to what you actually asked for, nothing speculative bolted on. `crucible
skills discover meta/coding-discipline` shows the full list. It
activates automatically any time code is being written or changed.

### 5. Prove it honestly

"It looks right" is not proof. Two things happen here:

- **A check before you trust it** — write a small test that confirms
  the thing works, before you believe it works. That's
  **`meta/tdd`**: write the check first, watch it fail (because nothing
  exists yet), then write just enough code to make it pass. `crucible
  skills discover meta/tdd`.
- **A skeptical pass before you say "done"** — re-read what you
  actually built (not what you meant to build), try to break it, and
  only then call it finished. That's **`meta/but-for-real`** — it
  activates automatically whenever you or the agent are about to say
  "this works" or "ready to ship." `crucible skills discover
  meta/but-for-real`.

Both matter: TDD proves the thing does what you designed; the skeptical
pass proves you didn't fool yourself about what you designed.

### 6. Keep what you learned

Every project teaches you something — a mistake you don't want to
repeat, a trick that worked, a thing that confused you until it didn't.
Write one short note about it before you move on. Beginners who do this
get better faster than beginners who don't, because the lessons stop
evaporating between projects.

**`meta/teach-me`** builds this into a standing learning workspace —
a mission (why you're learning this), a running list of what you've
learned, and short lessons you can revisit. Say "teach me" or `crucible
skills discover meta/teach-me` to set it up once; after that it keeps
growing with you.

Alongside the learning record, **`meta/build-along-course`** can turn
this milestone into one module of a running HTML course that grows
with your project — say "add this to the course" or `crucible skills
discover meta/build-along-course`.

## When to break the loop

Not everything needs all six steps. If you're just poking at an idea
for five minutes — trying something in a scratch file to see if it's
even possible — steps 3 through 5 (spec, disciplined build, formal
proof) are overkill. Say so explicitly by typing the words
`crucible-mode: exploration` anywhere in your next message, and the
spec gate steps aside so you can sketch freely:

> "Just exploring today — crucible-mode: exploration. Can we try
> wiring the meetup date up to a public calendar link instead of a
> text file, just to see if it's even possible?"

The rule of thumb: a tiny experiment you might throw away skips steps
3–5. Anything you intend to keep, show someone, or build on top of
later goes through all six. The loop is judgment, not ritual — knowing
when a step doesn't earn its keep is part of learning to build things.

## Related

- `docs/LOOP.md` in the crucible repo
  (https://github.com/b17z/crucible/blob/main/docs/LOOP.md) — the full
  walkthrough with a worked example.
- `knowledge/the-loop-at-scale.md` — what this same loop looks like once
  you're not the one writing the code — a controller coordinating
  agents that build and review each other's work.
- `meta/build-along-course` — grows a course module alongside each
  proven milestone in step 6.
- `meta/delivery-loop` — the professional counterpart to this loop, for
  someone who already knows how to code and is running real delivery
  work end to end. Run `crucible skills discover meta/delivery-loop`.
