# Crucible

**Your team's standards, applied by Claude, every time.**

Claude without context applies generic best practices. Crucible loads *your* patterns—so Claude reviews code the way your team would, not the way the internet would.

```
├── Personas:      Domain-specific thinking (how to approach problems)
├── Knowledge:     Coding patterns and principles (what to apply)
├── Cascade:       Project → User → Bundled (customizable at every level)
└── Context-aware: Loads relevant skills based on what you're working on
```

**Why Crucible?**
- **Consistency** — Same checklist every time, for every engineer, every session
- **Automation** — Runs in CI and pre-commit, not just interactively
- **Institutional knowledge** — Your senior engineer's mental checklist, in the repo
- **Your context** — Security fundamentals plus *your* auth patterns, *your* conventions, *your* definition of "done"
- **Cost efficiency** — Filter with free tools first, LLM only on what needs judgment

> Not affiliated with Atlassian's Crucible.

## Install

```bash
pip install crucible-mcp
```

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

With hot reload (recommended for customization):

```json
{
  "mcpServers": {
    "crucible": {
      "command": "mcpmon",
      "args": ["--watch", "~/.crucible/", "--", "crucible-mcp"]
    }
  }
}
```

## How It Works

```
Code → Detect Domain → Load Personas + Knowledge → Claude with YOUR patterns

.sol file → web3 domain → security-engineer + SMART_CONTRACT.md → Knows your security rules
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `review(path)` | Full review: analysis + skills + knowledge |
| `review(mode='staged')` | Review git changes with skills + knowledge |
| `load_knowledge(files)` | Load specific knowledge files |
| `get_principles(topic)` | Load engineering knowledge by topic |
| `delegate_*` | Direct tool access (semgrep, ruff, slither, bandit) |
| `check_tools()` | Show installed analysis tools |

The unified `review` tool supports:
- **Path-based**: `review(path="src/")` - analyze files/directories
- **Git-aware**: `review(mode="staged")` - analyze changes (staged, unstaged, branch, commits)
- **Quick mode**: `review(path, include_skills=false)` - analysis only, no skills/knowledge

## CLI

```bash
crucible init                     # Initialize .crucible/ for your project
crucible review                   # Review staged changes
crucible review --mode branch     # Review current branch vs main
crucible ci generate              # Generate GitHub Actions workflow

crucible skills list              # List all skills
crucible skills init <skill>      # Copy to .crucible/ for customization

crucible knowledge list           # List all knowledge files
crucible knowledge init <file>    # Copy for customization

crucible hooks install            # Install pre-commit hook
```

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full flow.

## Customization

Override skills and knowledge for your project or personal preferences:

```bash
# Customize a skill for your project
crucible skills init security-engineer
# Creates .crucible/skills/security-engineer/SKILL.md

# Add project-specific concerns, team conventions, etc.
```

Resolution order (first found wins):
1. `.crucible/` — Project overrides
2. `~/.claude/crucible/` — User preferences
3. Bundled — Package defaults

See [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) for the full guide.

## What's Included

**18 Personas** — Domain-specific thinking: security, performance, accessibility, web3, backend, and more.

See [SKILLS.md](docs/SKILLS.md) for the full list.

**12 Knowledge Files** — Coding patterns and principles for security, testing, APIs, databases, smart contracts, etc.

See [KNOWLEDGE.md](docs/KNOWLEDGE.md) for topics covered.

## Documentation

| Doc | What's In It |
|-----|--------------|
| [FEATURES.md](docs/FEATURES.md) | Complete feature reference |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How MCP, tools, skills, and knowledge fit together |
| [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) | Override skills and knowledge for your project |
| [SKILLS.md](docs/SKILLS.md) | All 18 personas with triggers and focus areas |
| [KNOWLEDGE.md](docs/KNOWLEDGE.md) | All 12 knowledge files with topics covered |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Adding tools, skills, and knowledge |

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests (509 tests)
ruff check src/ --fix     # Lint
```
