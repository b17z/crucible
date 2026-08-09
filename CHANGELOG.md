# Changelog

## 2.0.0 (2026-08-09)

### The v2 restructure

- **Phases 0–4** — MCP-first to skills-first restructure: `skills_core` loader primitives, 19 personas rebuilt in v2 shape (later 32 bundled skills), three-tier progressive disclosure (96.8% context reduction), trigger routing + spec gate, 7 Claude Code hooks.
- **Phase 5** — during-coding hooks: `PreToolUse` Bash deny-list, Edit/Write assertion pre-check, baseline snapshots with config-diff on `FileChanged`/`ConfigChange`/`SubagentStop`, and subagent skill inheritance.
- **Phase 6** — deterministic false-positive verifier (125/125 known-FP corpus suppressed) plus an opt-in LLM escalation tier and parallel static-analysis delegation for wall-clock.
- **Phase 7** — policy layer: schema + validator for the three bundled policies, GUARDRAILS Sign machinery (deny → candidate → `crucible-sign` ack → Stop append), and REVIEW.md conventions with advisory review-trigger nudges.
- **Phase 8** — structured dogfood pass across the full v2 surface, deferred-minor burn-down, and this release.

### Notable fixes

- Pre-commit gate now honors inline `# crucible-ignore:` suppressions instead of re-flagging them.
- Retired model pins replaced with current model aliases.
- Live-API tests are now guarded (`tests/conftest.py` blocks accidental network calls during the suite).
- Deny-path fail-open hardened against a surrogate `file_path` that could flip a deny decision to allow.
- LLM compliance assertions in `crucible review` are now opt-in via `--llm` (previously on by default when credentials existed).

### Known deferred

- repo_root-aware cascade loading for bindings/assertions (#TBD)
- no-git text mode hides inline-suppressed findings that git mode shows (#TBD)
- policy cascade has no user tier (deliberate scope choice, diverges from other cascades) (#TBD)
- mcp 2.x migration, lifting the `mcp<2.0.0` cap (#11)
- `review_nudge.sh` silently no-ops on a repo with no commits yet instead of nudging (#TBD)
- `meta/spec-validator`'s trigger regex misses several natural feature-request phrasings (#TBD)
- `crucible init --with-claudemd` doc/spec wording implies it creates `GUARDRAILS.md`; it's lazily created on first acknowledged Sign instead (#TBD)
