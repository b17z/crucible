# crucible

Code review MCP server. Runs static analysis tools and returns findings with domain metadata. Claude uses the domain info to load relevant review skills.

## Architecture

```
MCP (crucible)          Skills (Claude)           Claude
─────────────────       ─────────────────         ─────────────────
quick_review(path)  →   domains_detected    →     Loads relevant skills
                        severity_summary          (security-engineer,
                        findings                   web3-engineer, etc.)

                                                  Synthesizes review
                                                  Surfaces tensions
```

**MCP provides data. Skills provide perspective. Claude orchestrates.**

## Install

```bash
pip install -e ".[dev]"

# Install review skills to ~/.claude/skills/crucible/
crucible skills install
```

## Usage

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "crucible": {
      "command": "crucible-mcp"
    }
  }
}
```

Then in Claude Code:

```
# Run static analysis - returns findings + domain metadata
quick_review(path="src/Vault.sol")
→ domains_detected: solidity, smart_contract, web3
→ severity_summary: {critical: 1, high: 3}
→ Slither findings, Semgrep findings

# Claude sees "smart_contract" domain, loads web3-engineer skill
# Skill provides questions, red flags, approval criteria
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| `quick_review(path)` | Run analyzers, return findings + domains |
| `get_principles(topic?)` | Load engineering checklists |
| `delegate_semgrep(path)` | Direct semgrep access |
| `delegate_ruff(path)` | Direct ruff access |
| `delegate_slither(path)` | Direct slither access |
| `check_tools()` | Show installed analysis tools |

Domain detection is internal - `quick_review` returns `domains_detected` metadata that Claude uses to select skills.

## Skills

Review perspectives, installed via `crucible skills install`:

| Skill | Triggers | Focus |
|-------|----------|-------|
| `security-engineer` | auth, secrets, injection | Threat models, input validation |
| `web3-engineer` | solidity, smart_contract | Reentrancy, CEI pattern, gas |

More personas available in `knowledge/SENIOR_ENGINEER_CHECKLIST.md` - can be converted to skills as needed.

## External Tools

crucible shells out to these (install separately):

```bash
pip install semgrep           # Multi-language patterns
pip install ruff              # Python linting
pip install slither-analyzer  # Solidity analysis
```

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests
ruff check src/ --fix     # Lint
```

## Structure

```
src/crucible/
├── server.py           # MCP server (6 tools)
├── cli.py              # crucible skills install/list
├── models.py           # Domain, Severity, ToolFinding
├── domain/
│   └── detection.py    # Classify code by extension/content
├── tools/
│   └── delegation.py   # Shell out to semgrep, ruff, slither
├── knowledge/
│   └── loader.py       # Load principles markdown
└── skills/
    ├── security-engineer/SKILL.md
    └── web3-engineer/SKILL.md

knowledge/
├── ENGINEERING_PRINCIPLES.md    # Core engineering philosophy
└── SENIOR_ENGINEER_CHECKLIST.md # 21 persona checklists (reference)
```
