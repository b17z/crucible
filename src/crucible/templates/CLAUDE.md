# {project_name}

Use Crucible for code review: `crucible review`

For full engineering principles and patterns, run:
- `crucible knowledge list` - see available knowledge
- `crucible skills list` - see available review personas

## Progressive skill loading (three tiers)

Crucible skills load in three tiers to keep context cost low — don't
pull a skill's full body until you need it:

- **Tier 1 (discovery):** `crucible skills discover` — or the
  `discover_skills` MCP tool with no argument — lists every skill's name
  and one-line description. Cheap; call it at session start to see what
  review perspectives exist (~4 KB for ~27 skills vs ~120 KB to load all
  bodies).
- **Tier 2 (activation):** `crucible skills discover <name>` (or
  `discover_skills` with a `skill` argument) loads one skill's full
  SKILL.md body plus the names of its knowledge files. Do this when a
  skill is actually relevant to the task.
- **Tier 3 (knowledge):** load a specific knowledge file only when the
  activated skill points you to it (e.g. `security-engineer` →
  `knowledge/supply-chain-2026.md` when reviewing dependency changes).

Namespaced skills use a `prefix/name` identity — e.g. `meta/but-for-real`,
`pre-write/prd`. Pass that full name to discover/activate.

### Behavioral meta-skills

Beyond review personas, Crucible ships meta-skills that shape *how* the
agent works:

- **`meta/coding-discipline`** — think before coding, simplicity first,
  surgical changes, goal-driven execution. Adapted from Andrej
  Karpathy's observations on LLM coding pitfalls
  (`multica-ai/andrej-karpathy-skills`). It activates on
  implementation/editing intent; when writing or changing code, follow
  it: minimum code that solves the problem, surgical diffs, verify
  against success criteria.
- **`meta/but-for-real`** — skeptical second pass before declaring done.
- **`meta/spec-validator`** — gate feature requests on a spec.

## Crucible v2 plumbing in this project

Crucible v2 sets up a few project-level files this agent should be aware of:

- **`.crucible/baselines/`** — sha256 baselines for `.claude/settings.json`,
  `.mcp.json`, `.vscode/extensions.json`. The FileChanged hook compares
  live files against these baselines to catch the May 2026 TeamPCP TTP
  (silently modifying `.claude/settings.json` to install persistence).
  Run `crucible baselines init` once after setup; re-init only after
  investigating a divergence, never as a shortcut. The directory is
  gitignored — each contributor maintains their own.
- **`.crucible/approved-deps.yaml`** — durable allow-list for dependencies
  the npm/pip/cargo install gate has cleared. New deps must be added here
  (or session-approved via the `crucible-approve: <pkg>@<version>` magic
  comment) before the install gate will allow them. Pinned exact versions
  only; no ranges.
- **`AGENTS.md`** at the repo root — auto-generated pointer to this file.
  Other AI coding tools (Cursor, Codex, Gemini CLI) following the AGENTS.md
  convention discover the same per-repo instructions here. Don't edit it;
  edit `CLAUDE.md`.

## Threat landscape (May 2026)

The supply-chain threat picture changed materially in March-May 2026.
State actors are now spearphishing high-value maintainers; AI is writing
the malicious payloads. When reviewing any change that adds, updates, or
executes a dependency — or touches `.claude/settings.json`, `.mcp.json`,
`~/.npmrc`, `~/.pypirc`, `~/.ssh/`, or CI workflows — load the
`security-engineer` skill's `knowledge/supply-chain-2026.md` knowledge
file. It encodes the Axios compromise, Mini Shai-Hulud waves 1+2, the
May 20 GitHub breach, and the seven cross-cutting attack patterns the
review pass should be alert to.

## Magic comments

Crucible v2 watches user prompts for three magic-comment commands. These
are not slash commands — they're plain-text prefixes that
UserPromptSubmit hooks intercept:

- `crucible-approve: <name>@<version>` — **active.** Session-scoped
  approval for a package install. The magic-comments hook writes an
  entry into `.crucible/approved-deps.session.yaml`, which the
  npm/pip/cargo install gate reads. Equivalent to the durable
  allow-list but doesn't persist across sessions.
- `crucible-mode: exploration` — **partial.** The hook writes a flag to
  `.crucible/mode.session`. The consumer (the spec-validator gate that
  this flag is meant to bypass) ships in Phase 4. Until then, the flag
  is recorded but has no behavioral effect.
- `crucible-sign: <id> [<id>...]` — **partial.** The hook appends to
  `.crucible/inbox/signs-confirmed`. The Phase 7 GUARDRAILS.md
  auto-append flow that consumes this list — and the Stop-event summary
  that proposes Signs to confirm — ship in Phase 7. Until then, IDs are
  recorded but no GUARDRAILS.md entries are written.

If you rely on `crucible-mode: exploration` or `crucible-sign:` today,
check `.crucible/mode.session` / `.crucible/inbox/signs-confirmed`
directly — the side effect is real, but nothing else reads the file yet.

Cascade resolution applies across `.crucible/`, `~/.claude/crucible/`,
and bundled defaults. Project-local files override user-tier, which
overrides bundled. See `docs/CUSTOMIZATION.md` for details.
