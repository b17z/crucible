# Crucible

Code review MCP server for Claude. Runs static analysis and loads review skills based on what kind of code you're looking at.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Your Code  ──→  Crucible  ──→  Claude                                       │
│                  (analysis)     (synthesis)                                  │
│                                                                             │
│  .sol file  ──→  slither, semgrep  ──→  web3-engineer skill loaded          │
│  .py file   ──→  ruff, bandit      ──→  backend-engineer skill loaded       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**MCP provides data. Skills provide perspective. Claude orchestrates.**

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Install skills to ~/.claude/crucible/skills/
crucible skills install

# Install required analysis tools
pip install semgrep ruff
pip install slither-analyzer  # For Solidity
pip install bandit            # Optional, Python security
```

## MCP Setup

Add to your Claude Code `.mcp.json`:

```json
{
  "mcpServers": {
    "crucible": {
      "command": "crucible-mcp"
    }
  }
}
```

Then in Claude:

```
Review src/Vault.sol

→ Crucible: domains_detected: [solidity, smart_contract, web3]
→ Crucible: severity_summary: {critical: 1, high: 3}
→ Claude loads: web3-engineer, security-engineer skills
→ Claude synthesizes multi-perspective review
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `quick_review(path)` | Run analysis, return findings + domains |
| `get_principles(topic)` | Load engineering knowledge |
| `delegate_*` | Direct tool access (semgrep, ruff, slither, bandit) |
| `check_tools()` | Show installed analysis tools |

## CLI

```bash
crucible skills list              # List all skills
crucible skills show <skill>      # Show which version is active
crucible skills init <skill>      # Copy to .crucible/ for customization

crucible knowledge list           # List all knowledge files
crucible knowledge init <file>    # Copy for customization
```

## How It Works

Crucible detects what kind of code you're reviewing, runs the right analysis tools, and returns findings with domain metadata. Claude uses this to load appropriate review skills.

```
.sol file  →  slither + semgrep  →  web3-engineer, gas-optimizer skills
.py file   →  ruff + bandit      →  backend-engineer, security-engineer skills
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

**18 Review Skills** — Different review perspectives (security, performance, accessibility, web3, etc.)

See [SKILLS.md](docs/SKILLS.md) for the full list with triggers and focus areas.

**12 Knowledge Files** — Engineering principles for security, testing, APIs, databases, smart contracts, etc.

See [KNOWLEDGE.md](docs/KNOWLEDGE.md) for topics covered and skill linkages.

## Documentation

| Doc | What's In It |
|-----|--------------|
| [FEATURES.md](docs/FEATURES.md) | Complete feature reference |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | How MCP, tools, skills, and knowledge fit together |
| [CUSTOMIZATION.md](docs/CUSTOMIZATION.md) | Override skills and knowledge for your project |
| [SKILLS.md](docs/SKILLS.md) | All 18 review personas with triggers and key questions |
| [KNOWLEDGE.md](docs/KNOWLEDGE.md) | All 12 knowledge files with topics covered |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Adding tools, skills, and knowledge |

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests (263 tests)
ruff check src/ --fix     # Lint
```
