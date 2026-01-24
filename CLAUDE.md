# crucible

Code review orchestration MCP server. Composes static analysis tools (Slither, Semgrep, ESLint, Ruff) with engineering principles and multi-persona interpretation.

**Core insight:** The moat isn't detection — tools do that. The moat is **judgment at scale** through composable personas + evolving principles.

## Quick Reference

```bash
# Development
pip install -e ".[dev]"       # Install dev mode
pytest                        # Run tests
ruff check src/ --fix         # Lint
mypy src/ --strict            # Type check

# MCP Tools (via Claude Code)
review(code, domain?, personas?)     # Full review
quick_review(code)                   # Tool findings only (CI mode)
persona_review(code, persona)        # Single persona perspective
surface_tensions(reviews)            # Find where personas disagree
get_principles(topic?)               # Load principles
get_checklist(domain)                # Pre-ship checklist
```

## MCP Tools

| Tool | Purpose |
|------|---------|
| **Review** | |
| `review(code, domain?, personas?)` | Full review: tools + personas + synthesis |
| `quick_review(code)` | Fast review: tools only, no interpretation |
| `persona_review(code, persona)` | Single persona perspective |
| **Orchestration** | |
| `delegate_slither(path, detectors?)` | Smart contract analysis |
| `delegate_semgrep(path, config?)` | Multi-language pattern matching |
| `delegate_eslint(path)` | TypeScript/JavaScript linting |
| `delegate_ruff(path)` | Python linting |
| **Knowledge** | |
| `get_principles(topic?)` | Load engineering principles |
| `get_checklist(domain)` | Pre-ship checklist for domain |
| `get_persona_prompt(persona)` | Get persona's full prompt |
| **Analysis** | |
| `surface_tensions(reviews)` | Identify persona disagreements |
| `detect_domain(code)` | Auto-detect code domain |

## Architecture

```
crucible/
├── src/crucible/
│   ├── server.py            # MCP entry point (thin)
│   ├── tools/
│   │   ├── review.py        # Core review tools
│   │   ├── delegation.py    # Tool delegation (slither, semgrep, etc.)
│   │   └── knowledge.py     # Principles/checklist access
│   ├── domain/
│   │   ├── detection.py     # Auto-detect domain from code
│   │   └── routing.py       # Route to relevant personas
│   ├── personas/
│   │   ├── engine.py        # Invoke personas
│   │   └── tensions.py      # Detect disagreements
│   ├── synthesis/
│   │   └── synthesizer.py   # Combine findings into recommendation
│   └── knowledge/
│       ├── loader.py        # Load principles from files
│       └── principles/      # Structured YAML
├── tests/
└── knowledge/               # Raw markdown (source of truth)
```

## Key Modules

| File | Purpose |
|------|---------|
| `server.py` | MCP server, tool registration, stdio transport |
| `tools/review.py` | Main review orchestration |
| `tools/delegation.py` | Shell out to slither, semgrep, eslint, ruff |
| `domain/detection.py` | File extension + import pattern matching |
| `domain/routing.py` | Map domain → relevant personas |
| `personas/engine.py` | Load persona prompts, invoke, format output |
| `personas/tensions.py` | Compare reviews, find disagreements |
| `synthesis/synthesizer.py` | Combine everything into final output |
| `knowledge/loader.py` | Parse markdown/YAML principles |

## Domain Detection

Auto-detect from file content:

| Domain | Extensions | Import Patterns | Project Markers |
|--------|------------|-----------------|-----------------|
| `smart_contract` | `.sol` | `@openzeppelin`, `hardhat` | `contracts/` |
| `frontend` | `.tsx`, `.jsx` | `react`, `next`, `vue` | `package.json` with react |
| `backend` | `.py`, `.ts`, `.go` | `fastapi`, `express`, `gin` | API patterns |
| `infrastructure` | `.tf`, `.yaml` | terraform, k8s | `Dockerfile` |

## Personas

| Persona | Focus | Key Question |
|---------|-------|--------------|
| `security` | Threats, input validation | "What's the threat model?" |
| `web3` | Addresses, gas, MEV | "Is this address checksummed?" |
| `backend` | Scale, idempotency | "What happens at 10x load?" |
| `devops` | Observability, runbooks | "How do we know it's working?" |
| `product` | User value, metrics | "What problem does this solve?" |
| `performance` | Latency, complexity | "What's the hot path?" |
| `data` | Schema, migrations | "What's the source of truth?" |
| `pragmatist` | Ship it, simplicity | "Is this good enough?" |
| `purist` | Long-term maintainability | "Will we regret this?" |

### Persona Routing by Domain

```
smart_contract → [security, web3, gas_optimizer, protocol_architect]
frontend → [product, accessibility, uiux, performance]
backend → [security, backend, data, devops]
infrastructure → [devops, security, performance]
```

## Review Flow

```
1. DETECT DOMAIN
   → File: contracts/Vault.sol
   → Domain: smart_contract

2. DELEGATE TO TOOLS
   → slither-mcp.run_detectors(["reentrancy-eth"])
   → semgrep-mcp.scan(config="smart-contracts")
   
3. LOAD PRINCIPLES
   → ENGINEERING_PRINCIPLES.md
   → SMART_CONTRACT_SECURITY.md (domain-specific)

4. INVOKE PERSONAS
   → Security: "CRITICAL: Reentrancy in withdraw()"
   → Gas: "ReentrancyGuard adds 5k gas"
   → Protocol: "CEI pattern is cleaner"

5. SURFACE TENSIONS
   → Security vs Gas: ReentrancyGuard cost
   → Resolution: "Use CEI + Guard for mainnet"

6. SYNTHESIZE
   → Critical issues + persona perspectives + tensions + checklist
```

## Patterns

### Result Types (errors as values)

```python
from crucible.errors import Result, ok, err

def detect_domain(code: str) -> Result[Domain, str]:
    if ".sol" in code:
        return ok(Domain.SMART_CONTRACT)
    return err("Could not detect domain")
```

### Tool Delegation

```python
def delegate_semgrep(path: str, config: str = "auto") -> list[ToolFinding]:
    result = subprocess.run(
        ["semgrep", "--config", config, "--json", path],
        capture_output=True
    )
    return parse_semgrep_output(result.stdout)
```

### Persona Invocation

```python
def invoke_persona(persona: Persona, code: str, findings: list[ToolFinding]) -> PersonaReview:
    prompt = load_persona_prompt(persona)
    # ... invoke with findings context
    return PersonaReview(
        persona=persona,
        verdict="request_changes",
        concerns=["Reentrancy vulnerability"],
        approvals=["Good test coverage"],
        questions=["What's the expected gas cost?"]
    )
```

## Development

```bash
# Setup
pip install -e ".[dev]"
pre-commit install          # REQUIRED - secret detection

# Testing
pytest                      # All tests
pytest tests/test_detection.py -v  # Specific file
pytest -k "test_persona"    # Pattern match

# Quality
ruff check src/ --fix       # Lint + autofix
mypy src/ --strict          # Type check
```

## Core Principles

1. **Compose, don't rebuild** — Slither, Semgrep exist. Use them.
2. **Functional first** — Pure functions, errors as values, immutable data
3. **Types everywhere** — `mypy --strict` must pass
4. **Tests are mandatory** — Every feature needs unit + integration tests
5. **Config is user-tunable** — Thresholds configurable, not hardcoded

## Code Style

- Python 3.11+ (`match` statements, type parameter syntax)
- Frozen dataclasses for data models
- 100 char line length
- No `Any` types — use `Unknown` or proper generics
- Comments explain *why*, not *what*

## What NOT to Do

- Don't rebuild static analyzers — compose existing ones
- Don't add features not in SPEC.md
- Don't refactor while implementing a feature
- Don't create abstractions until the third duplication
- Don't leave TODO comments — do it or create an issue
- Don't use `Any` types
- Don't skip `pre-commit install`

## External Dependencies

These are **composed**, not rebuilt:

| Tool | What It Does | Installation |
|------|--------------|--------------|
| `slither` | Smart contract static analysis | `pip install slither-analyzer` |
| `semgrep` | Multi-language pattern matching | `pip install semgrep` |
| `eslint` | TypeScript/JavaScript linting | `npm install -g eslint` |
| `ruff` | Fast Python linting | `pip install ruff` |

For MCP composition (Phase 2+):
- slither-mcp: https://github.com/trailofbits/slither-mcp
- semgrep-mcp: https://github.com/semgrep/mcp

## Security (REQUIRED SETUP)

```bash
# Install pre-commit hooks FIRST
pre-commit install

# This enables:
# - gitleaks: comprehensive secret scanner
# - detect-secrets: second layer
# - detect-private-key: catches SSH/PGP keys
```

**Rule: Secrets NEVER belong in git. Ever.**

The `.gitignore` blocks:
- All `.env*` files
- Anything with `secret`, `password`, `credential` in the name
- All key formats (`.pem`, `.key`, etc.)
- Terraform state (often contains secrets)

## Don't Forget

- [ ] Run `pre-commit install` before writing any code
- [ ] Run tests before AND after changes
- [ ] New features need tests (unit + integration)
- [ ] Check SPEC.md for implementation details
- [ ] Types must pass `mypy --strict`
