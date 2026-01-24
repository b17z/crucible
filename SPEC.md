# crucible: MCP Server Specification

> A code review orchestration MCP that composes specialized analysis tools with engineering principles and multi-persona interpretation.

---

## What This Is

**crucible** is an MCP (Model Context Protocol) server that:

1. **Composes** existing analysis MCPs (slither, semgrep, eslint, ruff)
2. **Applies** your engineering principles as review context  
3. **Routes** to relevant senior engineer personas
4. **Surfaces** tensions between persona perspectives
5. **Synthesizes** actionable recommendations

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        crucible MCP                              │
│                   (orchestration + interpretation)                  │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  1. DETECT DOMAIN                                           │   │
│   │     .sol → smart_contract                                   │   │
│   │     .ts + react → frontend                                  │   │
│   │     .py + fastapi → backend                                 │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  2. DELEGATE TO SPECIALIZED MCPs                            │   │
│   │                                                             │   │
│   │     smart_contract → slither-mcp.run_detectors()            │   │
│   │     frontend → semgrep-mcp.scan() + eslint-mcp.lint()       │   │
│   │     backend → semgrep-mcp.scan() + ruff-mcp.check()         │   │
│   │     infra → checkov.scan()                                  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  3. LOAD PRINCIPLES + INVOKE PERSONAS                       │   │
│   │                                                             │   │
│   │     Load: ENGINEERING_PRINCIPLES.md                         │   │
│   │     Load: domain-specific principles                        │   │
│   │     Invoke: Security Auditor, Gas Optimizer, Pragmatist...  │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
│                              ▼                                      │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │  4. SYNTHESIZE                                              │   │
│   │                                                             │   │
│   │     Tool findings + Persona perspectives + Tensions         │   │
│   │     → Actionable recommendation                             │   │
│   └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘

External MCPs (you compose, don't build):
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  slither-mcp │ │  semgrep-mcp │ │  eslint-mcp  │ │   ruff-mcp   │
│  (ToB)       │ │  (Semgrep)   │ │  (ESLint)    │ │  (community) │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

---

## Domain Detection

Auto-detect domain from code context:

```python
DOMAIN_HEURISTICS = {
    "smart_contract": {
        "extensions": [".sol"],
        "imports": ["@openzeppelin", "hardhat", "foundry"],
        "dirs": ["contracts/", "src/contracts/"],
    },
    "frontend": {
        "extensions": [".tsx", ".jsx"],
        "imports": ["react", "next", "vue"],
        "deps": ["react", "next", "vue", "svelte"],
    },
    "backend": {
        "extensions": [".py", ".ts", ".go"],
        "imports": ["fastapi", "express", "gin"],
        "deps": ["fastapi", "express", "flask", "django"],
    },
    "infrastructure": {
        "extensions": [".tf", ".yaml", ".yml"],
        "patterns": ["Dockerfile", "docker-compose", "k8s/"],
    },
}
```

---

## Tool Interface

### Core Tools

```python
@tool
def review(
    code: str,
    domain: Domain | None = None,     # auto-detect if None
    personas: list[Persona] | None = None,  # domain-default if None
    context: str | None = None,       # additional context
) -> ReviewResult:
    """
    Full code review: tools + principles + personas + synthesis.
    
    Returns:
        ReviewResult with tool_findings, persona_reviews, tensions, synthesis
    """

@tool
def quick_review(code: str) -> QuickReviewResult:
    """
    Fast review: tools only, no persona interpretation.
    Good for CI/pre-commit hooks.
    """

@tool
def persona_review(
    code: str,
    persona: Persona,
    context: str | None = None,
) -> PersonaReview:
    """
    Single persona perspective on code.
    """

@tool
def surface_tensions(reviews: list[PersonaReview]) -> list[Tension]:
    """
    Identify where personas disagree.
    
    Example tension:
    - Security: "Use ReentrancyGuard on all external calls"
    - Gas Optimizer: "ReentrancyGuard adds ~5k gas, overkill for view functions"
    - Resolution hint: "Use on state-changing functions only"
    """
```

### Delegation Tools

```python
@tool
def delegate_slither(
    contract_path: str,
    detectors: list[str] | None = None,
) -> SlitherResult:
    """
    Delegate to slither-mcp for smart contract analysis.
    """

@tool
def delegate_semgrep(
    path: str,
    config: str = "auto",  # or specific ruleset
) -> SemgrepResult:
    """
    Delegate to semgrep-mcp for pattern matching.
    """

@tool
def delegate_eslint(path: str) -> ESLintResult:
    """Delegate to eslint-mcp for JS/TS linting."""

@tool
def delegate_ruff(path: str) -> RuffResult:
    """Delegate to ruff-mcp for Python linting."""
```

### Knowledge Tools

```python
@tool
def get_principles(topic: str | None = None) -> list[Principle]:
    """
    Get engineering principles, optionally filtered by topic.
    Topics: security, performance, testing, architecture, etc.
    """

@tool
def get_checklist(domain: Domain) -> list[ChecklistItem]:
    """
    Get pre-ship checklist for domain.
    """

@tool
def get_persona_prompt(persona: Persona) -> str:
    """
    Get the full prompt for a persona.
    Useful for understanding how a persona thinks.
    """
```

---

## Personas (from SENIOR_ENGINEER_CHECKLIST.md)

### Core Personas

| Persona | Focus | When to Lead |
|---------|-------|--------------|
| **Security Engineer** | Defense in depth, threat modeling | Money/auth/security-critical code |
| **Web3/Blockchain** | Smart contract patterns, MEV, gas | Any blockchain code |
| **Backend/Systems** | APIs, data flow, scalability | Core domain logic |
| **DevOps/SRE** | Observability, deployment, failure modes | Infrastructure changes |
| **Product Engineer** | User value, feature completeness | User-facing features |
| **Performance Engineer** | Speed, efficiency, bottlenecks | Hot paths, scale concerns |
| **Data Engineer** | Schema integrity, migrations | Database changes |
| **Accessibility Engineer** | WCAG, screen readers | UI components |
| **Mobile/Client** | Resource constraints, offline | Mobile/client code |
| **UI/UX Designer** | Visual consistency, UX patterns | Frontend components |
| **FDE/Solutions** | Customer configurability | Integration points |
| **Customer Success** | Support readiness, docs | Public-facing changes |
| **Tech Lead** | Architecture, team impact | Major changes |

### Meta-Personas

| Persona | Focus |
|---------|-------|
| **Pragmatist** | Ship it. Simplicity. Good enough. |
| **Purist** | Do it right. Long-term maintainability. |

---

## Data Models

```python
from enum import Enum
from dataclasses import dataclass

class Domain(Enum):
    SMART_CONTRACT = "smart_contract"
    FRONTEND = "frontend"
    BACKEND = "backend"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"

class Severity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Persona(Enum):
    SECURITY = "security"
    WEB3 = "web3"
    BACKEND = "backend"
    DEVOPS = "devops"
    PRODUCT = "product"
    PERFORMANCE = "performance"
    DATA = "data"
    ACCESSIBILITY = "accessibility"
    MOBILE = "mobile"
    UIUX = "uiux"
    FDE = "fde"
    CUSTOMER_SUCCESS = "customer_success"
    TECH_LEAD = "tech_lead"
    PRAGMATIST = "pragmatist"
    PURIST = "purist"

@dataclass
class ToolFinding:
    tool: str           # "slither", "semgrep", "eslint", "ruff"
    rule: str           # detector/rule name
    severity: Severity
    message: str
    location: str       # file:line or function name
    suggestion: str | None

@dataclass
class PersonaReview:
    persona: Persona
    verdict: str        # "approve", "request_changes", "comment"
    concerns: list[str]
    approvals: list[str]
    questions: list[str]

@dataclass
class Tension:
    personas: tuple[Persona, Persona]
    topic: str
    position_a: str
    position_b: str
    resolution_hint: str | None

@dataclass
class ReviewResult:
    domain: Domain
    tool_findings: list[ToolFinding]
    persona_reviews: list[PersonaReview]
    tensions: list[Tension]
    synthesis: str      # Final recommendation
    checklist: list[str]  # Remaining items to verify
```

---

## Directory Structure

```
crucible/
├── CLAUDE.md                    # Claude Code context
├── pyproject.toml               # Python package config
├── src/
│   └── crucible/
│       ├── __init__.py
│       ├── server.py            # MCP server entry point
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── review.py        # Core review tools
│       │   ├── delegation.py    # Tool delegation
│       │   └── knowledge.py     # Principles/checklist access
│       ├── domain/
│       │   ├── __init__.py
│       │   ├── detection.py     # Domain auto-detection
│       │   └── routing.py       # Persona routing logic
│       ├── personas/
│       │   ├── __init__.py
│       │   ├── engine.py        # Persona invocation
│       │   └── tensions.py      # Tension detection
│       ├── synthesis/
│       │   ├── __init__.py
│       │   └── synthesizer.py   # Final synthesis
│       └── knowledge/
│           ├── __init__.py
│           ├── loader.py        # Load principles from files
│           └── principles/      # Your principles as structured data
│               ├── engineering.yaml
│               ├── security.yaml
│               ├── smart_contracts.yaml
│               └── personas.yaml
├── tests/
│   ├── test_detection.py
│   ├── test_delegation.py
│   ├── test_personas.py
│   └── test_synthesis.py
└── knowledge/                   # Raw principles (source of truth)
    ├── ENGINEERING_PRINCIPLES.md
    ├── SENIOR_ENGINEER_CHECKLIST.md
    └── SMART_CONTRACT_SECURITY.md
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)
- [ ] MCP server skeleton (stdio transport)
- [ ] Domain detection from file extensions
- [ ] Single delegation: semgrep-mcp
- [ ] Load principles from markdown files
- [ ] Single persona: Security Engineer
- [ ] Basic synthesis (tool findings + persona review)

### Phase 2: Multi-Tool
- [ ] Add slither-mcp delegation (smart contracts)
- [ ] Add eslint-mcp delegation (TypeScript)
- [ ] Add ruff-mcp delegation (Python)
- [ ] Unified finding format across tools

### Phase 3: Multi-Persona
- [ ] All 13+ personas implemented
- [ ] Persona routing based on domain
- [ ] Tension detection algorithm
- [ ] Multi-persona synthesis

### Phase 4: Knowledge System
- [ ] Principles as structured YAML
- [ ] Domain-specific principle loading
- [ ] Checklist generation
- [ ] Principle citation in reviews

### Phase 5: Polish
- [ ] Quick review mode (CI-friendly)
- [ ] Caching for repeated reviews
- [ ] Configurable persona weights
- [ ] Custom principle injection

---

## Tech Stack

- **Language**: Python 3.11+
- **MCP SDK**: `mcp` (official Anthropic SDK)
- **Transport**: stdio (standard for MCP)
- **Config**: YAML for principles, TOML for package
- **Testing**: pytest
- **Linting**: ruff

---

## Example Flow

```
User: "Review this withdraw function before mainnet"

1. DETECT
   → File: contracts/Vault.sol
   → Domain: smart_contract

2. DELEGATE
   → slither-mcp.run_detectors(["reentrancy-eth", "unchecked-transfer"])
   → semgrep-mcp.scan(config="smart-contracts")
   
   Findings:
   - [HIGH] slither: reentrancy-eth in withdraw()
   - [MEDIUM] semgrep: unchecked-return-value on transfer

3. LOAD PRINCIPLES
   → ENGINEERING_PRINCIPLES.md (core philosophy)
   → SMART_CONTRACT_SECURITY.md (domain-specific)
   
4. INVOKE PERSONAS
   → Security Engineer: "CRITICAL: Reentrancy vulnerability. Add ReentrancyGuard."
   → Gas Optimizer: "ReentrancyGuard adds ~5k gas. Consider CEI pattern first."
   → Protocol Architect: "CEI is cleaner. Guard is belt-and-suspenders."
   → Incident Response: "If this deploys, we need monitoring on withdraw()"
   
5. SURFACE TENSIONS
   → Security vs Gas: ReentrancyGuard cost
   → Resolution: "Use CEI pattern AND ReentrancyGuard for mainnet. Gas cost acceptable for security."

6. SYNTHESIZE
   ```
   ## Critical Issues
   1. **Reentrancy vulnerability** in withdraw() [slither, Security Engineer]
      - Fix: Implement CEI pattern + ReentrancyGuard
      - Gas impact: ~5k per call (acceptable for security-critical function)
   
   ## Persona Perspectives
   - Security: Block until fixed
   - Gas: Acceptable cost
   - Protocol: Supports defense-in-depth
   
   ## Pre-Ship Checklist
   - [ ] Implement CEI pattern
   - [ ] Add ReentrancyGuard
   - [ ] Add withdraw monitoring
   - [ ] Test with slither --detect reentrancy
   ```
```

---

## References

- **Trail of Bits**: https://github.com/crytic/slither, https://github.com/trailofbits/slither-mcp
- **Semgrep MCP**: https://github.com/semgrep/mcp
- **ESLint MCP**: https://eslint.org/docs/latest/use/mcp
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Your Principles**: https://github.com/b17z/engineering_principles
