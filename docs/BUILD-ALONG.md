# Build-Along: Start a New Project With Crucible

A start-to-finish guide for beginning a brand-new project with
Crucible, from an empty folder to a working first milestone — with a
short interactive course that grows alongside the project as you go.
No prior experience assumed.

If you haven't seen it yet, read [LOOP.md](LOOP.md) first — it
explains the six-step engineering loop this guide follows. This guide
is that loop, applied start to finish to a brand-new project, plus the
course that grows alongside it.

---

## What "build-along" means

As you build, a second thing grows next to your project: a short
interactive HTML course that teaches what you built and why, one
module per finished milestone. The very first module — module 0 —
is your spec itself, so the course exists before a single line of
code does. Each module after that covers only what the most recent
milestone added, using real snippets from your own project.

The course lives in your project, in a `course/` folder, and opens in
any browser straight from disk — no server, no external requests,
works offline forever. Nobody writes it for you by hand: the
`meta/build-along-course` skill writes it, one module at a time, when
you ask for it or when a milestone in the loop just got proven. Run
`crucible skills discover meta/build-along-course` any time to see
exactly what it does.

The course is invited, not enforced. If you don't want a module for a
given milestone, just say so and move on — nothing blocks on it.

---

## Check your toolbox first

If you've never done software work on this computer, the basics may
be missing. You need two tools: `git` (keeps a history of your work)
and `uv` (installs Python tools into their own clean space). Check
both — paste each line and see whether it prints a version number:

```bash
git --version
uv --version
```

If both print versions, skip ahead to Setup. If either is missing:

**macOS.** Install Homebrew first — it's how Macs get developer
tools, and installing it also pulls in git's prerequisites. Paste
this into the Terminal app yourself, not into your agent (it asks
for your Mac login password, which an agent can't type for you):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

The script explains what it will do and pauses before doing it. When
it finishes, it prints a short "Next steps" note — paste those lines
too (they put `brew` on your PATH). Then install both tools:

```bash
brew install git uv
```

**Windows.** In a terminal: `winget install --id Git.Git`, then the
uv installer from https://docs.astral.sh/uv (one PowerShell line).

**Linux.** Install git with your package manager (for example
`sudo apt install git`), then uv with its official script:
`curl -LsSf https://astral.sh/uv/install.sh | sh`.

Two rules that keep this safe: your agent should never run `sudo` —
the only password moments are the Homebrew installer or your Linux
package manager, and you run those yourself in your own terminal.
And when Claude Code asks you to approve a command, that's the
guardrail working, not something going wrong: approve it once you
understand what it's for, and if a command the agent needs keeps
getting refused, run it yourself in the Terminal and paste back what
it printed.

Why `uv` and not plain `pip`? Modern systems protect their built-in
Python ("externally managed"), so bare `pip install` often fails with
a confusing error. `uv` installs tools into their own space and puts
them on your PATH — no fighting the system.

---

## Setup

These commands are copy-pasteable as written. If you're starting from
a completely empty folder, create it and turn it into a git repository
first:

```bash
mkdir my-project && cd my-project
git init
```

Install Crucible from GitHub (it isn't published on PyPI yet):

```bash
uv tool install "git+https://github.com/b17z/crucible.git"
```

If `crucible --version` doesn't work afterwards, run
`uv tool update-shell` and open a fresh terminal. (Already a
developer with a working Python environment? `pip install
"git+https://github.com/b17z/crucible.git"` into your venv works
too.)

Initialize Crucible in your project, with a minimal `CLAUDE.md` so
Claude Code knows it's there:

```bash
crucible init --with-claudemd
```

Wire up the Claude Code hooks, so the right skills activate
automatically as you work:

```bash
crucible hooks claudecode init
```

Optional: if you keep notes in your notes folder — any tool that
reads markdown from a directory (Obsidian, Logseq, an in-house
notetaker) — and want your learning records to land there instead of
inside the project folder, create `.crucible/teach.yaml` with a
`vault:` key pointing at that folder's path:

```yaml
vault: /path/to/your/notes/folder
```

If you skip this, learning records stay inside the project instead —
either way works, and you can add the vault later.

---

## The loop, with a course module per milestone

From here, follow the six-step engineering loop (see
[LOOP.md](LOOP.md) for the full explanation of each step):

1. **Say it plainly** — one sentence, no jargon, for what you're
   building right now.
2. **Think small first** — `meta/brainstorming` finds the smallest
   version worth building.
3. **Write it down** — three to five sentences become your spec.
   `meta/spec-validator` makes sure this happens before code gets
   written.
4. **Build the smallest thing** — only the one small step, nothing
   speculative. `meta/coding-discipline` keeps this honest.
5. **Prove it honestly** — a test first (`meta/tdd`), then a skeptical
   pass before calling it done (`meta/but-for-real`).
6. **Keep what you learned** — a learning record via `meta/teach-me`,
   and — new here — a course module via `meta/build-along-course`. As
   soon as you write your spec, that's course module 0; every proven
   milestone after that can become one more module.

Run `crucible skills discover meta/engineering-loop` for the full
skill, or `crucible skills discover meta/build-along-course` for the
course skill specifically. Repeat the loop, one milestone at a time,
for as many milestones as your project needs.

---

## Worked example: a personal knowledge base in a notes folder

Say the project is: **a personal knowledge base built on top of your
notes folder** — any tool that reads markdown from a directory
(Obsidian, Logseq, an in-house notetaker) — a tool that helps organize
and surface notes already sitting there. Here's how the loop and the
course play out together, milestone by milestone.

**Milestone 0 — the spec.** Before any code, three to five sentences
get written down: "A tool that reads notes from my notes folder and
helps me organize them. It creates a folder skeleton for a new topic
area. It parses note frontmatter into a structured index. It shows an
overview board of notes by status. Later, it automates moving notes
between stages." That spec becomes course module 0 — before anything
else exists, the course already explains what's being built and why.

**Milestone 1 — vault skeleton.** The smallest first step: a script
that creates a consistent folder structure for a new topic area inside
the vault (an index note, a subfolder per category). Built small,
tested, proven. That becomes course module 1 — using the real
folder-creation code just written, with a why-should-I-care opening
("why bother with a consistent skeleton instead of just dropping notes
wherever?") and a quiz that checks understanding, not memorization.

**Milestone 2 — the parser.** Reads each note's frontmatter (the small
block of structured metadata at the top of a note) and builds an index
of what exists. Proven with a test against a handful of sample notes.
Course module 2 covers just this diff — what frontmatter is, why
parsing it beats re-typing the same information twice, with a real
snippet from the parser.

**Milestone 3 — the board.** A simple view that groups notes by status
(drafting, active, archived) using the index the parser built.
Course module 3 covers this milestone alone — not the parser again,
not the whole project restated, just what changed.

**Milestone 4 — automation.** A small rule that moves a note from one
status folder to another when a condition in its frontmatter changes.
Course module 4 closes out the example.

By the end, the course has five modules — the spec plus one per proven
milestone — each teaching only what its own milestone added, in plain
language, from the learner's own code.

---

## Kickoff Prompt template

Copy the block below into a fresh Claude Code session to bootstrap a
new project with Crucible end to end. Fill in the three placeholders
first — project name, where your spec file lives (or will live), and
your vault path if you're using one.

```text
I'm starting a new project called <PROJECT-NAME>. Here's what I need
you to do, in order:

0. Before anything else, check my toolbox — I may not have a dev
   environment at all. Run `git --version` and `uv --version`. If
   either is missing, help me install the basics first. On macOS:
   have me install Homebrew myself in the Terminal app (the official
   one-line command from https://brew.sh — it asks for my Mac
   password, which you can't type for me), have me paste its "Next
   steps" PATH lines when it finishes, then run `brew install git uv`
   yourself. On Windows: `winget install --id Git.Git` plus the uv
   installer from https://docs.astral.sh/uv. On Linux: git via my
   package manager, uv via its official install script. Never run
   `sudo` yourself. Verify both tools print versions before moving
   on. As you work, the app will ask me to approve commands — tell
   me plainly what each one is for, and if a command you need keeps
   getting refused, give me the exact command to run myself and I'll
   paste back what it printed.

1. If this directory isn't already a project, set it up: create the
   project directory if it doesn't exist, `cd` into it, and run
   `git init` if it isn't already a git repository.

2. Install Crucible from GitHub and initialize it:
   uv tool install "git+https://github.com/b17z/crucible.git"
   crucible init --with-claudemd
   crucible hooks claudecode init
   If `crucible --version` fails after the install, run
   `uv tool update-shell` and ask me to open a fresh session.

3. Read the spec at <SPEC-FILE>. Do not start building yet. If
   <SPEC-FILE> doesn't exist yet, don't invent it — help me write it
   first via `meta/brainstorming` and `crucible prewrite`.

4. Run `crucible prewrite review <SPEC-FILE>` and fix anything it
   flags before writing any code.

5. Follow the `meta/engineering-loop` skill (run `crucible skills
   discover meta/engineering-loop` if you want the details) starting
   from the spec's own v1 scope, one milestone at a time. Use the
   spec's own sequencing if it defines one; otherwise pick the
   smallest first milestone yourself and confirm it with me before
   building.

6. Once the spec is confirmed, use `meta/build-along-course` (run
   `crucible skills discover meta/build-along-course` for details) to
   create course module 0 from the spec. After each milestone is
   built and proven, offer me one more course module covering just
   that milestone — don't build one unless I say yes.

7. Write learning records (via `meta/teach-me`) to <VAULT-PATH> as you
   go. If <VAULT-PATH> is empty or not set, keep learning records
   inside the project instead.

Do NOT build anything beyond the spec's v1 scope without checking with
me first. Do NOT skip the "prove it honestly" step (a test before the
code is trusted, a skeptical pass before anything is called done) for
any milestone, even a small one.
```

---

## Related

- [LOOP.md](LOOP.md) — the six-step engineering loop this guide walks
  through end to end.
- [`meta/engineering-loop`](../src/crucible/skills/meta/engineering-loop/SKILL.md) — the skill behind the loop; `crucible skills discover meta/engineering-loop`.
- [`meta/build-along-course`](../src/crucible/skills/meta/build-along-course/SKILL.md) — the skill that grows the course; `crucible skills discover meta/build-along-course`.
- [QUICKSTART.md](QUICKSTART.md) — a shorter, non-beginner-focused install guide.
