# crucible

Claude Code customization layer. Personas for domains, knowledge for patterns, customizable at every level.

## Quick Reference

```bash
pip install -e ".[dev]"    # Install
pytest                     # Test (509 tests)
ruff check src/ --fix      # Lint
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `review(path)` | Unified review: analysis + skills + knowledge |
| `review(mode='staged')` | Git-aware review with skills + knowledge |
| `load_knowledge(files)` | Load specific knowledge files |
| `get_principles(topic)` | Load engineering knowledge by topic |
| `delegate_*` | Direct tool access (semgrep, ruff, slither, bandit) |
| `check_tools()` | Show installed tools |

## CLI Commands

```bash
crucible init                     # Initialize .crucible/ for project
crucible review                   # Review staged changes
crucible review --mode branch     # Review branch vs main
crucible ci generate              # Generate GitHub Actions workflow

crucible skills list              # List all skills
crucible skills init <skill>      # Copy for project customization

crucible knowledge list           # List all knowledge files
crucible knowledge init <file>    # Copy for customization

crucible hooks install            # Install pre-commit hook
```

## Project Structure

```
src/crucible/
├── server.py           # MCP server (unified review tool)
├── cli.py              # CLI commands
├── models.py           # Domain, Severity, ToolFinding
├── errors.py           # Result types (Ok/Err)
├── domain/detection.py # Classify code by extension/content
├── tools/delegation.py # Shell out to analysis tools
├── knowledge/          # 12 bundled knowledge files
└── skills/             # 18 bundled persona skills
```

## Patterns

**Errors as values:**
```python
from crucible.errors import Result, ok, err

def do_thing() -> Result[Value, str]:
    if bad:
        return err("what went wrong")
    return ok(value)
```

**Frozen dataclasses:**
```python
@dataclass(frozen=True)
class ToolFinding:
    tool: str
    rule: str
    severity: Severity
    message: str
    location: str
```

## Cascade Resolution

Skills and knowledge follow priority (first found wins):
1. `.crucible/skills/` or `.crucible/knowledge/` (project)
2. `~/.claude/crucible/` (user)
3. bundled (package)

## Commit Messages

Format: `(type): description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Documentation

See `docs/` for:
- FEATURES.md - Complete feature reference
- ARCHITECTURE.md - How pieces fit together
- CUSTOMIZATION.md - Skill/knowledge cascade
- SKILLS.md - All 18 personas
- KNOWLEDGE.md - All 12 knowledge files
- CONTRIBUTING.md - For contributors
