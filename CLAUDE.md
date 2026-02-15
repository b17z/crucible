# crucible

Code review with enforcement. Patterns that block bad code, not just suggest fixes.

## Quick Reference

```bash
pip install -e ".[dev]"    # Install
pytest                     # Test (630+ tests)
ruff check src/ --fix      # Lint
```

## Key 1.0 Features

- **30 bundled assertions** - security, error handling, smart contracts
- **Pre-commit hook** - `crucible hooks install`
- **Claude Code hook** - `crucible hooks claudecode init`
- **Pattern + LLM assertions** - fast/free + semantic/costs

## MCP Tools

| Tool | Purpose |
|------|---------|
| `review(path)` | Unified review: analysis + skills + knowledge + assertions |
| `review(mode='staged')` | Git-aware review with enforcement |
| `prewrite_review(path)` | Review specs/PRDs before code is written |
| `prewrite_list_templates()` | List available pre-write templates |
| `load_knowledge(files)` | Load specific knowledge files |
| `get_principles(topic)` | Load engineering knowledge by topic |
| `delegate_*` | Direct tool access (semgrep, ruff, slither, bandit) |
| `check_tools()` | Show installed tools |

## CLI Commands

```bash
crucible init --with-claudemd     # Initialize + minimal CLAUDE.md
crucible review                   # Review staged changes
crucible review --mode branch     # Review branch vs main
crucible review src/ --no-git     # Review without git

crucible hooks install            # Git pre-commit hook
crucible hooks claudecode init    # Claude Code hooks (PostToolUse + SessionStart)

crucible system init              # Create .crucible/system/ templates
crucible system show              # Preview session context injection

crucible assertions list          # List assertion files
crucible assertions test file.py  # Test assertions

crucible skills init <skill>      # Copy for customization
crucible knowledge init <file>    # Copy for customization

crucible prewrite list            # List pre-write templates
crucible prewrite init prd my.md  # Create spec from template
crucible prewrite review spec.md  # Review spec against assertions

crucible ignore show              # Show active ignore patterns
crucible ignore init              # Create .crucible/.crucibleignore
crucible ignore test <path>       # Test if path would be ignored
```

## Project Structure

```
src/crucible/
├── server.py              # MCP server
├── cli.py                 # CLI commands
├── models.py              # Domain, Severity, ToolFinding
├── errors.py              # Result types (Ok/Err)
├── ignore.py              # .crucibleignore file handling
├── enforcement/           # Assertions, patterns, compliance
│   ├── bundled/           # 30 bundled assertions
│   ├── assertions.py      # Load and resolve
│   ├── patterns.py        # Pattern matching
│   └── compliance.py      # LLM assertions
├── hooks/                 # Git and Claude Code hooks
│   ├── precommit.py       # Pre-commit hook logic
│   └── claudecode.py      # Claude Code hooks (PostToolUse, SessionStart)
├── history.py             # Session continuity (recent findings)
├── prewrite/              # Pre-write spec review
│   ├── loader.py          # Template loading with cascade
│   ├── review.py          # Pre-write review logic
│   └── models.py          # PrewriteMetadata, PrewriteResult
├── templates/prewrite/    # 5 bundled spec templates
├── knowledge/             # 14 bundled knowledge files
└── skills/                # 20 bundled persona skills
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
class EnforcementFinding:
    assertion_id: str
    message: str
    severity: str
    location: str
```

## Cascade Resolution

Skills, knowledge, assertions, templates, and ignore patterns follow priority (first found wins):
1. `.crucible/` (project)
2. `~/.claude/crucible/` (user)
3. bundled (package)

## Ignore Patterns

`.crucibleignore` uses gitignore syntax. Built-in defaults exclude:
- `node_modules/`, `.git/`, `__pycache__/`, `.venv/`
- `.next/`, `.nuxt/`, `dist/`, `build/`
- `package-lock.json`, `yarn.lock`, `*.log`

Create `.crucible/.crucibleignore` to add project-specific patterns.

## Session Context (Activation Energy)

Claude Code's SessionStart hook injects context automatically:
- **enforcement.md** - Auto-generated summary of active assertions
- **.crucible/system/*.md** - Team patterns, focus areas, conventions
- **.crucible/history/recent-findings.md** - Last review results

Run `crucible hooks claudecode init` to enable. Create custom context with `crucible system init`.

## Commit Messages

Format: `(type): description`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Documentation

See `docs/` for:
- QUICKSTART.md - 5-minute setup guide
- FEATURES.md - Complete feature reference
- ARCHITECTURE.md - How pieces fit together
- CUSTOMIZATION.md - Skill/knowledge/assertion cascade
- SKILLS.md - All 20 personas
- KNOWLEDGE.md - All 14 knowledge files
- CONTRIBUTING.md - For contributors
