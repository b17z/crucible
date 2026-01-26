# crucible

Claude Code customization layer. Personas for domains, knowledge for patterns, customizable at every level.

## Quick Reference

```bash
pip install -e ".[dev]"    # Install
pytest                     # Test (263 tests)
ruff check src/ --fix      # Lint
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `quick_review(path)` | Run analysis, return findings + domains |
| `get_principles(topic)` | Load engineering knowledge |
| `delegate_semgrep/ruff/slither/bandit` | Direct tool access |
| `check_tools()` | Show installed tools |

## CLI Commands

```bash
crucible skills list              # List all skills
crucible skills install           # Install to ~/.claude/crucible/
crucible skills init <skill>      # Copy for project customization
crucible skills show <skill>      # Show resolution cascade

crucible knowledge list/install/init/show  # Same for knowledge
```

## Project Structure

```
src/crucible/
├── server.py           # MCP server (7 tools)
├── cli.py              # Skills/knowledge management
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
