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

All core personas have been implemented (20 skills). Potential future additions:

- compliance-engineer (GDPR, SOC2, HIPAA)
- ml-engineer (model deployment, inference optimization)
- api-designer (REST/GraphQL best practices)
- testing-engineer (test strategy, coverage gaps)

---

## ~~Project-Level Skill Overrides~~ ✓ IMPLEMENTED

Cascade resolution is now implemented:

```
.crucible/skills/<skill>/SKILL.md       # Project override
~/.claude/crucible/skills/<skill>/       # User default
<package>/skills/<skill>/                # Bundled
```

Use `crucible skills init <skill>` to copy bundled skill for customization.

---

## ~~CI Integration~~ ✓ IMPLEMENTED

CLI now supports:
- `crucible review --fail-on <severity>` — Exit non-zero on findings
- `crucible review --json` — JSON output for CI parsing
- `crucible review --format report` — Markdown audit reports
- Config-based per-domain thresholds in `.crucible/review.yaml`
