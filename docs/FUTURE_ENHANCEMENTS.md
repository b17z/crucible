# Future Enhancements

Ideas for future development. Not currently implemented.

## Tension Detection

Currently, Claude synthesizes tensions naturally when multiple skills are loaded. Potential enhancements:

### Option 1: Explicit tensions.md per skill

Each skill declares known conflicts:

```markdown
# security-engineer/tensions.md
conflicts_with:
  - performance-engineer: "Input validation adds latency"
  - pragmatist: "Security often requires more code"
```

### Option 2: Synthesis prompt template

Add a structured prompt that explicitly asks Claude to surface conflicts:

```markdown
## Tension Analysis
After reviewing with all perspectives, identify:
1. Where do the personas disagree?
2. What's the trade-off?
3. What context would change the recommendation?
```

### Option 3: Do nothing (current)

Let Claude figure it out. Skills provide perspectives, Claude naturally identifies conflicts. This is probably sufficient - Claude is good at holding multiple viewpoints.

**Recommendation:** Start with Option 3, add explicit guidance only if Claude consistently misses important tensions.

---

## Additional Skills

Potential future skills not yet implemented:

- mobile-engineer
- uiux-engineer
- fde-engineer (field/solutions engineer)
- customer-success
- gas-optimizer (web3-specific)
- protocol-architect (web3-specific)
- mev-researcher (web3-specific)
- formal-verification
- incident-responder

---

## Project-Level Skill Overrides

Support config cascade for skills:

```
<project>/.claude/skills/crucible/security-engineer/SKILL.md  # Project override
~/.claude/skills/crucible/security-engineer/SKILL.md          # User default
<crucible>/src/crucible/skills/security-engineer/SKILL.md     # Package default
```

CLI could support: `crucible skills override security-engineer`

---

## CI Integration

`quick_review` returns structured data suitable for CI:

```bash
crucible-mcp quick_review src/ --format json | jq '.severity_summary.critical'
```

Could add exit codes based on severity thresholds.
