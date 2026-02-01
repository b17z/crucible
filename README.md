# Crucible

**Your team's standards, applied by Claude, every time.**

Claude without context applies generic best practices. Crucible loads *your* patterns—so Claude reviews code the way your team would, not the way the internet would.

```
├── Enforcement:   Pattern + LLM assertions that block bad code
├── Personas:      Domain-specific thinking (how to approach problems)
├── Knowledge:     Coding patterns and principles (what to apply)
├── Cascade:       Project → User → Bundled (customizable at every level)
└── Context-aware: Loads relevant skills based on what you're working on
```

**Why Crucible?**
- **Enforcement** — Not suggestions, constraints. Assertions block code that violates your patterns
- **Consistency** — Same checklist every time, for every engineer, every session
- **Automation** — Runs in CI, pre-commit hooks, and Claude Code hooks
- **Institutional knowledge** — Your senior engineer's mental checklist, in the repo
- **Your context** — Security fundamentals plus *your* auth patterns, *your* conventions
- **Cost efficiency** — Filter with free tools first, LLM only on what needs judgment

> Not affiliated with Atlassian's Crucible.

## Quick Start

```bash
pip install crucible-mcp

# Initialize your project
crucible init --with-claudemd

# Install enforcement hooks
crucible hooks install              # Git pre-commit
crucible hooks claudecode init      # Claude Code hooks
```

That's it. Crucible will now:
1. Run on every commit (pre-commit hook)
2. Review files Claude edits (Claude Code hook)
3. Block code that violates bundled assertions (security, error handling, smart contracts)

## How Enforcement Works

```
Claude writes code
    ↓
PostToolUse hook triggers
    ↓
Crucible runs pattern assertions
    ↓
Finding detected → Exit 2 (block) + feedback to Claude
    ↓
Claude fixes the issue
```

**30 bundled assertions** covering:
- Security: eval, exec, shell injection, pickle, hardcoded secrets, SQL injection
- Error handling: bare except, silent catch, empty catch blocks
- Smart contracts: reentrancy, CEI violations, access control, tx.origin auth

**Customize with your own assertions** in `.crucible/assertions/`:

```yaml
# .crucible/assertions/my-rules.yaml
version: "1.0"
name: my-rules
assertions:
  - id: no-console-log
    type: pattern
    pattern: "console\\.log\\("
    message: "Remove console.log before committing"
    severity: warning
    priority: medium
    languages: [javascript, typescript]
```

## MCP Tools

Add to Claude Code (`.mcp.json`):

```json
{
  "mcpServers": {
    "crucible": {
      "command": "crucible-mcp"
    }
  }
}
```

| Tool | Purpose |
|------|---------|
| `review(path)` | Full review: analysis + skills + knowledge + assertions |
| `review(mode='staged')` | Review git changes with enforcement |
| `load_knowledge(files)` | Load specific knowledge files |
| `get_principles(topic)` | Load engineering knowledge by topic |
| `delegate_*` | Direct tool access (semgrep, ruff, slither, bandit) |
| `check_tools()` | Show installed analysis tools |

## CLI

```bash
# Review
crucible review                     # Review staged changes
crucible review --mode branch       # Review current branch vs main
crucible review src/file.py --no-git # Review without git

# Assertions
crucible assertions list            # List all assertion files
crucible assertions test file.py    # Test assertions against a file

# Hooks
crucible hooks install              # Install pre-commit hook
crucible hooks claudecode init      # Initialize Claude Code hooks

# Customize
crucible skills init <skill>        # Copy skill for customization
crucible knowledge init <file>      # Copy knowledge for customization

# CI
crucible ci generate                # Generate GitHub Actions workflow
```

## Customization

Everything follows cascade resolution (first found wins):
1. `.crucible/` — Project overrides (checked into repo)
2. `~/.claude/crucible/` — User preferences
3. Bundled — Package defaults

**Override a skill:**
```bash
crucible skills init security-engineer
# Edit .crucible/skills/security-engineer/SKILL.md
```

**Add project knowledge:**
```bash
crucible knowledge init SECURITY
# Edit .crucible/knowledge/SECURITY.md
```

**Add custom assertions:**
```bash
mkdir -p .crucible/assertions
# Create .crucible/assertions/my-rules.yaml
```

See [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for the full guide.

## What's Included

**30 Bundled Assertions** — Pattern rules for security, error handling, and smart contracts.

**18 Personas** — Domain-specific thinking: security, performance, accessibility, web3, backend, and more.

**14 Knowledge Files** — Coding patterns and principles for security, testing, APIs, databases, smart contracts, etc.

See [SKILLS.md](docs/SKILLS.md) and [KNOWLEDGE.md](docs/KNOWLEDGE.md) for details.

## Documentation

| Doc | What's In It |
|-----|--------------|
| [QUICKSTART.md](docs/QUICKSTART.md) | 5-minute setup guide |
| [FEATURES.md](docs/FEATURES.md) | Complete feature reference |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How MCP, tools, skills, and knowledge fit together |
| [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) | Override skills and knowledge for your project |
| [SKILLS.md](docs/SKILLS.md) | All 18 personas with triggers and focus areas |
| [KNOWLEDGE.md](docs/KNOWLEDGE.md) | All 14 knowledge files with topics covered |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Adding tools, skills, and knowledge |

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests (580+ tests)
ruff check src/ --fix     # Lint
```
