# crucible

Code review MCP server. Runs static analysis tools and loads engineering checklists based on what kind of code you're looking at.

## Quick Reference

```bash
pip install -e ".[dev]"    # Install
pytest                     # Test
ruff check src/ --fix      # Lint

# Skill management
crucible skills list                    # List all skills
crucible skills install                 # Install skills to ~/.claude/skills/
crucible skills init <skill>            # Copy skill to .crucible/skills/ for customization
crucible skills show <skill>            # Show skill resolution cascade
```

## What's Implemented

| Tool | Purpose |
|------|---------|
| `quick_review(path)` | Run analyzers, return findings + domains |
| `get_principles(topic?)` | Load engineering checklists |
| `delegate_semgrep(path)` | Direct semgrep access |
| `delegate_ruff(path)` | Direct ruff access |
| `delegate_slither(path)` | Direct slither access |
| `delegate_bandit(path)` | Direct bandit access (Python security) |
| `check_tools()` | What's installed |

Domain detection is internal - `quick_review` returns `domains_detected` metadata for skill selection. For Python files, `quick_review` runs ruff + bandit + semgrep by default.

## Project Structure

```
src/crucible/
├── server.py           # MCP server (7 tools)
├── models.py           # Domain, Persona, ToolFinding
├── errors.py           # Result types (Ok/Err)
├── domain/
│   └── detection.py    # Extension + content matching
├── tools/
│   └── delegation.py   # Shell out to analysis tools
└── knowledge/
    └── loader.py       # Parse persona markdown

knowledge/
├── ENGINEERING_PRINCIPLES.md
└── SENIOR_ENGINEER_CHECKLIST.md

skills/                         # 18 bundled persona skills
├── security-engineer/
├── web3-engineer/
├── backend-engineer/
└── ...
```

## Skill Resolution

Skills are loaded with cascade priority (first found wins):

```
1. <project>/.crucible/skills/<skill>/SKILL.md   # Project-level (highest)
2. ~/.claude/skills/crucible/<skill>/SKILL.md    # User-level
3. <package>/skills/<skill>/SKILL.md             # Bundled (lowest)
```

Use `crucible skills init <skill>` to copy a skill for project customization.

## Patterns

**Errors as values:**
```python
from crucible.errors import Result, ok, err

def do_thing() -> Result[Value, str]:
    if bad:
        return err("what went wrong")
    return ok(value)
```

**Frozen dataclasses for models:**
```python
@dataclass(frozen=True)
class ToolFinding:
    tool: str
    rule: str
    severity: Severity
    message: str
    location: str
```

## Development

```bash
pytest                        # Run tests
pytest tests/test_X.py -v     # Specific file
ruff check src/ --fix         # Lint
```

**Before committing:**
- Tests pass
- Ruff clean
- New features have tests

## Sage Memory

Use Sage for persistent memory across sessions.

```
sage_health()                           # Session start
sage_recall_knowledge(query="...")      # Before starting work
sage_autosave_check(trigger="synthesis", core_question="...", current_thesis="...", confidence=0.X)
sage_save_knowledge(id="...", content="...", keywords=[...])
```

## Commit Messages

Format: `(type): description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

```
(feat): add tension detection
(fix): handle empty semgrep output
(docs): update persona table
```

## External Tools

Install separately:

```bash
pip install semgrep           # Required
pip install ruff              # Required
pip install slither-analyzer  # For .sol files
```
