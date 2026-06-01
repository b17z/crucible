# GUARDRAILS.md

Things this project's coding agent should NOT do.

This file lives alongside `CLAUDE.md` and is the negative-space companion
to it. Where `CLAUDE.md` says what to do, `GUARDRAILS.md` records the
failure modes — patterns the agent did once, that produced a real problem,
and shouldn't be repeated. Each entry is a **Sign**.

Crucible populates this file on the `Stop` event with explicit user
acknowledgement (via the `crucible-sign: <ids>` magic comment).
Unacknowledged candidate Signs collect in `.crucible/inbox/` for later
review. PostToolUse never mutates this file directly — that path leads
to spam.

## Sign format

```markdown
### Sign N — <short title>

- **Trigger:** <what condition this Sign fires on — file path, prompt
  pattern, tool call shape>
- **Instruction:** <what NOT to do, phrased as a rule>
- **Reason:** <one-line history of the incident this came from>
- **Provenance:** <date, session, optional issue link>
```

## Signs

_(none yet — Crucible appends here on user `crucible-sign:` acknowledgement)_
