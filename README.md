# crucible

Code review MCP server. Detects what kind of code you're looking at, runs the right static analysis tools, and loads relevant engineering checklists.

## Install

```bash
pip install -e ".[dev]"
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
# Detect what kind of code this is
detect_domain(code="pragma solidity ^0.8.0; ...")
→ Domain: smart_contract
→ Personas: security, web3, gas_optimizer, ...

# Get a specific persona's checklist
get_persona(persona="security")
→ Questions they ask, red flags, approval criteria

# Run static analysis
quick_review(path="src/")
→ Findings from semgrep, ruff, slither (based on file types)

# Full review with persona context
review(code="...", file_path="Vault.sol")
→ Domain + relevant persona perspective
```

## MCP Tools

| Tool | What it does |
|------|-------------|
| `detect_domain` | Classify code as smart_contract, frontend, backend, infrastructure |
| `get_principles` | Load engineering principles by topic |
| `get_persona` | Get a persona's checklist (security, web3, backend, etc.) |
| `quick_review` | Run static analysis tools, return findings |
| `review` | Detect domain + load relevant persona perspective |
| `delegate_semgrep` | Run semgrep directly |
| `delegate_ruff` | Run ruff directly |
| `delegate_slither` | Run slither directly |

## Personas

21 review personas, routed by domain:

| Domain | Personas |
|--------|----------|
| `smart_contract` | security, web3, gas_optimizer, protocol_architect, mev_researcher, incident_responder |
| `frontend` | product, accessibility, uiux, performance, mobile |
| `backend` | security, backend, data, devops, performance |
| `infrastructure` | devops, security, performance |

Each persona has key questions, red flags, and approval criteria. See `knowledge/SENIOR_ENGINEER_CHECKLIST.md`.

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
├── server.py           # MCP server
├── models.py           # Domain, Persona, ToolFinding types
├── domain/
│   └── detection.py    # Classify code by extension/content
├── tools/
│   └── delegation.py   # Shell out to semgrep, ruff, slither
└── knowledge/
    └── loader.py       # Load personas from markdown

knowledge/
├── ENGINEERING_PRINCIPLES.md    # Core engineering philosophy
└── SENIOR_ENGINEER_CHECKLIST.md # 21 persona checklists
```
