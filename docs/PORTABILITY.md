# Portability

What Crucible needs from a harness, and what changes when that
harness isn't Claude Code.

---

## The contract

Crucible's only real requirement is an agent with shell access and a
place to put project instructions. Skills are markdown files, read by
whatever agent has been told to read them. The CLI is the API — every
capability (`crucible review`, `crucible skills discover`, `crucible
prewrite review`, ...) is a shell command with no hidden dependency on
a specific harness or IDE integration.

Git-aware review modes (`crucible review`, `--mode staged`, `--mode
branch`) use git to scope what gets reviewed, but git is not a hard
requirement: `crucible review <path> --no-git` runs static analysis
over a path directly, no repository required.

## The matrix

| Harness | Reads | Activation |
|---|---|---|
| Claude Code (any model backend, gateways included) | `CLAUDE.md` + hooks | Full auto-activation: PostToolUse/SessionStart hooks fire, `core/trigger_router.py` matches prompts to skills, session context injects automatically, enforcement gates (spec-validator, install gates) block without being asked. |
| Codex, Gemini CLI, pi, Cursor | `AGENTS.md` | CLI-driven, no auto-fire. The agent reads `AGENTS.md` like any other project instructions file, and skills only activate when `AGENTS.md` tells it to run `crucible skills discover` at session start and to call `crucible review` before finishing. |

`crucible init` generates `AGENTS.md` as a pointer at `CLAUDE.md` for
every project, so Codex/Cursor/etc. see the same per-repo instructions
Claude Code does — but without hooks, nothing fires on its own. The
harness has to be told to ask.

Minimum viable `AGENTS.md` snippet for a non-hook harness:

```markdown
Crucible is installed in this project (`crucible` on PATH).
At the start of every session, run `crucible skills discover` to see
available review skills, and activate any that are relevant.
Before finishing a task, run `crucible review` and address findings.
```

## Models

Nothing in the loop skills, the enforcement gates, or the trigger
router is model-specific — they're prose and pattern matching, and
they run the same regardless of which model is behind the harness.
The one exception is the opt-in LLM assertion tier (`crucible review
--llm`), which calls the Anthropic API for semantic checks that plain
pattern matching can't do. Everything else — pattern assertions,
skills, hooks, trigger routing, `--no-git` review — has no Anthropic
dependency at all.

## Related

- [QUICKSTART.md](QUICKSTART.md) — installing and setting up Crucible.
- [CUSTOMIZATION.md](CUSTOMIZATION.md) — the skill/knowledge/assertion
  cascade this doc assumes.
