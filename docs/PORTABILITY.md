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
| Claude Code (any model backend, gateways included) | `CLAUDE.md` + hooks | Full auto-activation across the event set in use — `UserPromptSubmit` (`core/trigger_router.py` matches prompts to skills, magic comments) fires trigger routing, `PreToolUse` enforces gates, `PostToolUse` runs review, `SessionStart` injects session context, and `Stop` handles signs and nudges — all without being asked. |
| Codex, Gemini CLI, pi, Cursor | `AGENTS.md` | CLI-driven, no auto-fire. The agent reads `AGENTS.md` like any other project instructions file, and skills only activate when `AGENTS.md` tells it to run `crucible skills discover` at session start and to call `crucible review` before finishing. |

`crucible init --with-claudemd` generates `AGENTS.md` as a pointer at
`CLAUDE.md`, so Codex/Cursor/etc. see the same per-repo instructions
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

Three surfaces call the Anthropic API directly, and none of them
degrade gracefully without a key:

- `crucible review --llm` — the opt-in LLM assertion tier, for
  semantic checks plain pattern matching can't do.
- `crucible review --verify-llm` — the LLM-backed false-positive
  verifier (`verify/llm.py`).
- `crucible prewrite review` — not opt-in. `cmd_prewrite_review` in
  `cli.py` hardcodes `ComplianceConfig(enabled=True)`, so every
  `prewrite review` invocation calls Anthropic per assertion
  (`prewrite/review.py`).

That last one has a sharp edge: with no `ANTHROPIC_API_KEY` set, each
assertion call fails independently with an `"Anthropic API key not
found"` error, the run collects zero findings, and `crucible prewrite
review` exits 0 — printed and read as "passed." **If prewrite review's
output shows key-not-found errors, the semantic gate did not run** —
check the errors section before trusting a pass; a clean exit code
alone doesn't mean the spec was reviewed.

Everything else — pattern assertions, hooks, skills, `crucible
review`'s deterministic tier, delegated scanners (semgrep, ruff,
slither, bandit), trigger routing, `--no-git` review — has no
Anthropic dependency at all.

## Related

- [QUICKSTART.md](QUICKSTART.md) — installing and setting up Crucible.
- [CUSTOMIZATION.md](CUSTOMIZATION.md) — the skill/knowledge/assertion
  cascade this doc assumes.
