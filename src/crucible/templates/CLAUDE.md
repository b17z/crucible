# {project_name}

Use Crucible for code review: `crucible review`

For full engineering principles and patterns, run:
- `crucible knowledge list` - see available knowledge
- `crucible skills list` - see available review personas

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

- `crucible-mode: exploration` — bypass the spec-validator gate for this
  session only. Auto-expires at session end. The bypass count surfaces
  in the session summary.
- `crucible-approve: <name>@<version>` — session-scoped approval for a
  package install. Equivalent to the durable allow-list but doesn't
  persist across sessions.
- `crucible-sign: <id> [<id>...]` — confirm pending GUARDRAILS.md Signs
  proposed at the previous Stop event. Phase 7 owns the auto-append flow;
  the magic comment is the user's ack.

Cascade resolution applies across `.crucible/`, `~/.claude/crucible/`,
and bundled defaults. Project-local files override user-tier, which
overrides bundled. See `docs/CUSTOMIZATION.md` for details.
