---
name: teach-me
description: Use when the user says "teach me", "I want to learn", or asks to be taught a new skill or concept over multiple sessions. Builds a stateful teaching workspace — mission, resources, learning records, glossary, and short self-contained lessons — grounded in why the user wants the skill and calibrated to their zone of proximal development. Do NOT use for a one-off clarification of something already said (use wait-what) or for reviewing code/specs — this is multi-session skill and knowledge acquisition.
version: "2.0"
---

> Adapted from mattpocock/skills (MIT, © 2026 Matt Pocock). See THIRD-PARTY-NOTICES.md.

# Teach Me

The user has asked to be taught something. This is a stateful request —
they intend to learn the topic over multiple sessions.

## Teaching workspace

Treat the current directory as a teaching workspace. The state of the
user's learning is captured in files there:

- `MISSION.md` — the _reason_ the user is interested in the topic. Use
  this to ground all teaching. Format: `knowledge/mission-format.md`.
- `RESOURCES.md` — trusted sources to draw knowledge from and
  communities to draw wisdom from. Format:
  `knowledge/resources-format.md`.
- `GLOSSARY.md` — the canonical language for this workspace. Format:
  `knowledge/glossary-format.md`.
- `learning-records/*.md` — what the user has learned, loosely
  equivalent to architectural decision records: non-obvious lessons and
  key insights that may need to be revised later, or that drive future
  sessions. Titled `0001-<dash-case-name>.md`, incrementing. Format:
  `knowledge/learning-record-format.md`.
- `lessons/*.html` — self-contained HTML lessons, one tightly-scoped
  thing each, tied to the mission. The primary unit of teaching.
- `assets/*` — reusable components shared across lessons (stylesheets,
  quiz widgets, simulators, diagram helpers).
- `reference/*` — compressed cheat-sheets and quick-reference documents
  distilled from lessons (syntax tables, glossaries of technique,
  process flowcharts) — the things worth revisiting after the lesson
  itself is forgotten.
- `NOTES.md` — a scratchpad for user preferences or working notes.

`lessons/`, `assets/`, and `reference/` ALWAYS stay in the workspace,
regardless of vault configuration (see below) — they're HTML-leaning
output, not notes, and don't belong in a notes vault.

## Vault resolution

Before writing any workspace file, resolve where `MISSION.md`,
`learning-records/`, `RESOURCES.md`, `NOTES.md`, and `GLOSSARY.md`
live, in this exact order:

1. Check `.crucible/teach.yaml` in the project for a `vault:` key
   (project-level).
2. If not set there, check `~/.claude/crucible/teach.yaml` for a
   `vault:` key (user-level).
3. If a vault is set by either: `MISSION.md`, `learning-records/`,
   `RESOURCES.md`, `NOTES.md`, and `GLOSSARY.md` live under
   `<vault>/crucible-learning/<topic-slug>/` instead of the workspace.
   `lessons/`, `assets/`, and `reference/` still stay in the workspace
   — never write HTML-leaning artifacts into the vault.
4. If no vault is set anywhere: fall back to pure upstream
   workspace-only behavior (everything under the current directory, as
   described above) — AND, on first use in a workspace with no vault
   configured, ask the user once whether they'd like learning saved to
   their notes folder — any tool that reads markdown from a directory
   (Obsidian, Logseq, an in-house notetaker) — offering to write the
   config (project or user `teach.yaml`, per their preference) if they
   say yes. Don't ask again in that workspace once they've answered
   either way.

## Philosophy

To learn at a deep level, the user needs three things:

- **Knowledge**, captured from high-quality, high-trust resources.
- **Skills**, acquired through highly-relevant interactive lessons you
  devise, based on the knowledge.
- **Wisdom**, which comes from interacting with other learners and
  practitioners.

Before `RESOURCES.md` is well-populated, your focus should be to find
high-quality resources which will help the user acquire knowledge. Never
trust your parametric knowledge.

Some topics may require more skills than knowledge. Learning more about
theoretical physics might be more knowledge-based. For yoga, more
skills-based.

### Fluency vs. storage strength

Be careful to split between two types of learning:

- **Fluency strength** — in-the-moment retrieval of knowledge.
- **Storage strength** — long-term retention of knowledge.

Fluency can give the user an illusory sense of mastery, but storage
strength is the real goal. Design lessons that build long-term retention
through desirable difficulty:

- Retrieval practice (recall from memory)
- Spacing (distributing practice over time)
- Interleaving (mixing up different but related topics — for skills
  practice only)

## Lessons

A lesson is the main thing you produce — the unit in which knowledge and
skills reach the user. Each lesson is one self-contained HTML file,
saved to `lessons/` and titled `0001-<dash-case-name>.html` where the
number increments each time.

A lesson should be **beautiful** — clean, readable typography and
layout — since the user will return to these later to review. Think
Tufte.

The lesson should be short and completable very quickly. Learners'
working memory is small, and you need to stay within it. But each lesson
should give the user a single tangible win they can build on. It should
be directly tied to the mission, and should be in the user's zone of
proximal development.

If possible, open the lesson file for the user by running a CLI command.

Each lesson should:

- Link via HTML anchors to other lessons and reference documents.
- Recommend a primary source for the user to read or watch — the most
  high-quality, high-trust resource you found on the topic.
- Contain a reminder to ask followup questions. The agent is the
  teacher, and can assist with anything unclear.

## Assets

Lessons are built from reusable **components**, stored in `assets/`:
stylesheets, quiz widgets, simulators, diagram helpers — anything a
second lesson could reuse.

Reuse is the default, not the exception. Before authoring a lesson, read
`assets/` and build from the components already there. When a lesson
needs something new and reusable, write it as a component in `assets/`
and link to it — never inline code a future lesson would duplicate.

A shared stylesheet is the first component every workspace earns: every
lesson links it, so the lessons look like one consistent course rather
than a pile of one-offs. As the workspace grows, so should the component
library.

## The mission

Every lesson should be tied into the mission — the reason the user is
interested in learning about the topic.

If the user is unclear about the mission, or `MISSION.md` is not
populated, your first job should be to question the user on why they
want to learn this.

Failing to understand the mission will mean knowledge acquisition is not
grounded in real-world goals. Lessons will feel too abstract. You will
have no way of judging what the user should do next.

Missions may change as the user develops more skills and knowledge. This
is normal — update `MISSION.md` and add a learning record to capture the
change. Confirm with the user before changing the mission.

## Zone of proximal development

Each lesson, the user should always feel as if they are being challenged
"just enough."

The user may specify an exact thing they want to learn. If they don't,
figure out their zone of proximal development by:

- Reading their learning records.
- Figuring out the right thing to teach them based on their mission.
- Teaching the most relevant thing that fits in their zone of proximal
  development.

## Knowledge

Lessons should be designed around a skill the user is going to learn.
The knowledge in the lesson should be only what's required to acquire
that skill. Teach the knowledge first, then get the user to practice the
skills via an interactive feedback loop.

Knowledge should first be gathered from trusted resources. Use
`RESOURCES.md` to keep track of them. Lessons should be littered with
citations — links to external resources to back up any claim made. This
increases the trustworthiness of the lesson.

For acquiring knowledge, difficulty is the enemy. It eats working memory
needed for understanding.

## Skills

If knowledge is all about acquisition, skills are about durability and
flexibility. Make the knowledge stick.

For skill acquisition, difficulty is the tool. Effortful retrieval is
what builds storage strength. Skills should be taught through
interactive lessons. Tools at your disposal:

- Interactive lessons, using quizzes and light in-browser tasks.
- Lessons which guide the user through a list of real-world steps to
  take (for instance, yoga poses).

Each of these should be based on a **feedback loop**, where the user
receives feedback on their performance. This feedback loop should be as
tight as possible, giving feedback immediately — and ideally
automatically.

For quizzes, each answer should be exactly the same number of words (and
characters, if possible). Don't give the user any clues about the answer
through formatting.

## Acquiring wisdom

Wisdom comes from true real-world interaction — testing skills outside
the learning environment.

When the user asks a question that appears to require wisdom, your
default posture should be to attempt to answer — but to ultimately
delegate to a **community**.

A community is a place (online or offline) where the user can test
their skills in the real world: a forum, a subreddit, a real-world
class, a local interest group.

Attempt to find high-reputation communities the user can join. If the
user expresses a preference not to join a community, respect it.

## Reference documents

While creating lessons, also create reference documents. Lessons can
reference these — they're useful for tracking raw units of knowledge
useful across lessons.

Lessons will rarely be revisited later — reference documents will be.
They should be the compressed essence of the lesson, in a format
designed for quick reference.

Some learning topics lend themselves to reference:

- Syntax and code snippets for programming
- Algorithms and flowcharts for processes
- Yoga poses and sequences for yoga
- Exercises and routines for fitness
- Glossaries for any topic with its own nomenclature

Glossaries, in particular, are essential reference. Once one is created,
adhere to it in every lesson.

## `NOTES.md`

The user will sometimes express preferences of how they want to be
taught, or things you should keep in mind. Record those in `NOTES.md` so
you can refer back to them when designing lessons or working with the
user.

## Knowledge

- `knowledge/mission-format.md` — `MISSION.md` template and rules.
- `knowledge/learning-record-format.md` — learning-record template,
  numbering, and when to write one.
- `knowledge/resources-format.md` — `RESOURCES.md` structure and
  curation rules.
- `knowledge/glossary-format.md` — `GLOSSARY.md` structure and rules.
