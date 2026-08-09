# crucible

Code review with enforcement. Patterns that block bad code, not just suggest fixes.

## Quick Reference

```bash
pip install -e ".[dev]"    # Install
pytest                     # Test (860+ tests)
ruff check src/ --fix      # Lint
```

## Key Features

- **42 bundled assertions** - security, error handling, smart contracts
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
crucible review --no-verify           # Raw findings (skip FP verifier)

crucible hooks install            # Git pre-commit hook
crucible hooks claudecode init    # Claude Code hooks (PostToolUse + SessionStart)

crucible system init              # Create .crucible/system/ templates
crucible system show              # Preview session context injection

crucible assertions list          # List assertion files
crucible assertions test file.py  # Test assertions

crucible policies validate        # Validate policy files
crucible signs list               # List pending and acked candidate Signs

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
│   ├── bundled/           # 42 bundled assertions
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
└── skills/                # 37 bundled persona skills
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
- SKILLS.md - All 37 bundled skills
- KNOWLEDGE.md - All 14 knowledge files
- CONTRIBUTING.md - For contributors

## Agent skills

### Issue tracker

GitHub Issues at `b17z/crucible`, managed via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical defaults (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). The four state labels get created on first use by the `triage` skill; `wontfix` already exists. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout — one `CONTEXT.md` and `docs/adr/` at the repo root (not yet created; the `grill-with-docs` skill populates them lazily). See `docs/agents/domain.md`.

### Bundled behavioral skills

Crucible ships meta-skills that shape *how* the agent works, discoverable via `crucible skills discover` (Tier 1) and activated by `core/trigger_router.py`:

- **`meta/coding-discipline`** — think before coding, simplicity first, surgical changes, goal-driven execution. Adapted from Andrej Karpathy's observations on LLM coding pitfalls. Activates on implementation/editing intent.
- **`meta/but-for-real`** — force a skeptical second pass before declaring work done.
- **`meta/spec-validator`** — gate feature requests on a spec; bypassable per-session with `crucible-mode: exploration`.
- **`meta/writing-good-skills`** — author/refactor a SKILL.md using mid-2026 practitioner consensus (description-as-trigger, the 8 antipatterns, the 3 eval pillars). Use it whenever creating or reviewing a skill.
- **`meta/break-it`** — adversarially QA a *running* product/agent by driving it like confused, impatient, over-trusting, or hostile users. The runtime counterpart to `but-for-real`. Ships persona/tour + agent-failure-mode references.
- **`meta/challenge`** — pressure-test a strategy/plan/thesis as a skeptical reviewer demanding tradeoffs and evidence (vs `but-for-real`, which verifies finished work).
- **`meta/brainstorming`** — hard-gates implementation behind a presented, approved design; one-question-at-a-time dialogue, YAGNI, spec self-review. Adapted from obra/superpowers.
- **`meta/systematic-debugging`** — root-cause-first debugging in four phases; blocks fixes proposed before Phase 1 completes. Adapted from obra/superpowers.
- **`meta/tdd`** — the red-green-refactor loop: seams, anti-patterns (implementation-coupled, tautological, horizontal slicing), one slice at a time. Adapted from mattpocock/skills.
- **`meta/wait-what`** — re-pitch an unclear message in plain language instead of repeating it louder. Adapted from mattpocock/skills.
- **`meta/teach-me`** — stateful, multi-session teaching workspace (mission, resources, learning records, glossary, lessons); vault-aware via `.crucible/teach.yaml`. Adapted from mattpocock/skills.

When writing or changing code in this repo, `meta/coding-discipline` applies: minimum code that solves the problem, surgical diffs, verify against success criteria. When authoring a skill, `meta/writing-good-skills` applies.

Full attribution (MIT license texts, source URLs) for the adapted skills above lives in `THIRD-PARTY-NOTICES.md`.
