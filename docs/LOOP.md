# The Engineering Loop

A plain-language guide to building your first thing, for anyone who has
never shipped software before. No prior experience assumed — every term
gets explained the first time it's used.

---

## What this is

Building software (a web page, an app, a small tool) is not one giant
leap from "idea" to "finished thing." It's six small steps, done in
order, repeated for every piece you build. Each step has a name, a
purpose, and a Crucible skill that helps you do it. This guide walks
through all six using one example from start to finish.

Crucible is set up so that saying what you want, in plain English, is
often enough to activate the right skill automatically. Where it isn't
automatic, this guide shows you exactly what to type.

---

## The worked example

Say you want: **a page that shows my running club's next meetup.**
You've never built a website before. Here's the whole loop, step by
step, using that example.

### Step 1 — Say it plainly

Type it exactly like you'd say it to a friend:

> "I want a web page that shows when my running club meets next."

No tool names, no jargon — just the plain sentence. That's the whole
step. If the agent's response back to you doesn't make sense — too much
unfamiliar language, or an explanation that goes over your head — say
so directly:

> "wait, what? can you explain that simply?"

That activates `meta/wait-what`, which re-explains in plain language
instead of repeating the same words louder. You can also run `crucible
skills discover wait-what` any time to see what it does.

### Step 2 — Think small first

Don't design the whole dream version (member logins, a event calendar,
RSVPs, a mobile app). Find the smallest version that could possibly
work. For the running club page, that's: one page, showing one date,
time, and location. Nothing else yet.

Say something like:

> "Let's build the smallest version of this — just today's next
> meetup, no login, no calendar."

This activates `meta/brainstorming`. The agent asks you questions one
at a time (where does the meetup info come from? does it need to work
on phones? do you want to be able to update it yourself?), proposes a
couple of options with trade-offs, and — this is the important
part — **does not write any code** until it has shown you a short plan
and you've said yes to it. If you want to see what this skill does
ahead of time: `crucible skills discover brainstorming`.

### Step 3 — Write it down

Once you and the agent agree on the small version, write down what
"done" means in three to five plain sentences. That's a spec — just a
short, agreed description of what you're building, written down so
nobody has to guess later. For the running club page, it might read:

> "A single web page. It shows the next meetup's date, time, and
> location. It updates when I edit one text file. No login, no
> database, no calendar — just the one page."

`meta/spec-validator` is the check that makes sure this happens before
code gets written — it's why, if you ask to "build" something without
having written this down first, the agent will pause and ask "is there
a spec for this?" instead of diving straight into code. `crucible
skills discover spec-validator` explains the check, and also how to
skip it on purpose for a five-minute experiment you don't intend to
keep (see "When to break the loop" below).

### Step 4 — Build the smallest thing

Now, and only now, code gets written — and only the small version from
step 3, nothing more. It's tempting to also add the calendar and the
RSVP form while you're in there; resist it. One small piece at a time
means when something's wrong, you know exactly where to look.

You don't need to say anything special here — `meta/coding-discipline`
activates automatically whenever code is being written or changed. It
keeps the agent's changes matched to what you actually asked for:
minimum code that solves the problem, nothing speculative bolted on
top. `crucible skills discover coding-discipline` shows the full list
of habits it enforces.

### Step 5 — Prove it honestly

"It looks right" is not proof that it works. Two checks happen here:

- **A check before you trust it.** Before believing the page shows the
  right date, there should be a small, automated check that confirms
  it — written *before* the page code, so you can watch it fail first
  (because the page doesn't exist yet) and then watch it pass once the
  page is built. That's `meta/tdd` — say "let's do this test-first" or
  it activates automatically once tests come up. `crucible skills
  discover tdd`.
- **A skeptical pass before calling it done.** Before anyone says
  "it's ready," the agent re-reads what was actually built (not what
  it meant to build), tries to break it (What if the text file is
  empty? What if the date format is wrong?), and only then calls it
  finished. That's `meta/but-for-real` — it activates automatically any
  time you or the agent are about to say "this works" or "ready to
  ship." `crucible skills discover but-for-real`.

Both matter for different reasons: the test proves the page does what
you designed it to do; the skeptical pass proves nobody fooled
themselves about what "working" means.

### Step 6 — Keep what you learned

Every project teaches you something. Maybe you learned that editing a
text file is easier than you expected, or that "no login" saved you
days of work, or that you got confused by a term until someone
explained it plainly. Write one short note about it before moving on —
this is how beginners get better faster than beginners who don't do
this, because the lessons stop disappearing between projects.

Say "teach me" once, or run `crucible skills discover teach-me`, and
`meta/teach-me` sets up a standing learning workspace for you: a
mission (why you're learning this), a running record of what you've
learned, and short lessons you can revisit later. After the first
setup, it keeps growing with you across future sessions.

**If you want that workspace to live in an Obsidian vault** instead of
just the project folder, `meta/teach-me` will ask you once, the first
time you use it, whether you'd like to save learning there — and offer
to write the small config file (`teach.yaml`) that remembers your
choice. Say yes and give it the vault path, or say no and everything
stays in the project. You won't be asked again after you answer.

---

## When to break the loop

Not everything needs all six steps. If you're just poking at an idea
for five minutes — trying something in a scratch file to see whether
it's even possible — steps 3 through 5 (writing a spec, disciplined
building, formal proof) are more ceremony than the moment calls for.
Say so explicitly by typing the words `crucible-mode: exploration`
anywhere in your next message, and the spec check steps aside so you
can sketch freely:

> "Just exploring today — crucible-mode: exploration. Can we try
> wiring the meetup date up to a public Google Calendar link instead
> of a text file, just to see if it's even possible?"

Rule of thumb: a tiny experiment you might throw away skips steps 3–5.
Anything you intend to keep, show someone, or build on top of later
goes through all six. Learning when a step doesn't earn its keep is
part of learning to build things — this is judgment, not a ritual to
follow blindly.

---

## The loop at scale

Everything above is the loop run by one person, in one sitting. The
same six habits — say it plainly, think small, write it down, build the
smallest thing, prove it honestly, keep what you learned — hold at a
much bigger scale too: when the "builder" isn't a single agent typing
code for you, but a whole team of agents building and checking each
other's work.

At that scale, the shape becomes: a coordinating agent that never
writes code itself, only hands out tasks and makes judgment calls; each
task done by a fresh agent with no memory of anything except that one
task, so its reasoning stays clean; a *second, independent* agent that
reviews the first one's work, because the person (or agent) who wrote
something is the worst-positioned to spot its own mistake; a "fix loop"
when the reviewer finds something, with a limit on how many rounds it
can go before a human gets pulled in; and a running record — a ledger —
of what's done and what's not, because memory doesn't survive a reset
but a file on disk does.

The payoff is the same reason the six-step loop works for one person:
independent, skeptical review catches things a confident, unchecked
single pass would have shipped looking completely fine.

For the full picture — the fresh-context reasoning, the fix-loop rules,
the ledger, and the habits that keep it honest — see the
`meta/engineering-loop` skill's knowledge file:
`src/crucible/skills/meta/engineering-loop/knowledge/the-loop-at-scale.md`.

---

## Related

- [`meta/engineering-loop`](../src/crucible/skills/meta/engineering-loop/SKILL.md) — the skill this guide accompanies; run `crucible skills discover engineering-loop` any time.
- [QUICKSTART.md](QUICKSTART.md) — installing and setting up Crucible itself.
- [SKILLS.md](SKILLS.md) — every bundled skill, including the six named above.
