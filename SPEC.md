# crucible: Architecture Specification

> Code review MCP server. Runs static analysis tools, returns findings with domain metadata. Claude loads relevant skills and synthesizes reviews.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Claude Code                                  │
│                                                                      │
│   User: "Review this withdraw function"                              │
│                                                                      │
│   ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│   │  crucible MCP   │────▶│  Skills Layer   │────▶│  Synthesis    │ │
│   │  (data)         │     │  (perspective)  │     │  (Claude)     │ │
│   └─────────────────┘     └─────────────────┘     └───────────────┘ │
│                                                                      │
│   quick_review()          security-engineer       Identifies         │
│   → domains_detected      web3-engineer           tensions,          │
│   → severity_summary      (auto-loaded)           recommends         │
│   → findings                                      actions            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Key insight:** MCP provides data, Skills provide perspective, Claude orchestrates.

---

## MCP Tools (6 total)

```python
@tool
def quick_review(path: str, tools: list[str] | None = None) -> ReviewResult:
    """
    Run static analysis tools on code.

    Returns:
        - domains_detected: ["solidity", "smart_contract", "web3"]
        - severity_summary: {"critical": 1, "high": 3}
        - findings: Grouped by tool (Slither, Semgrep, Ruff)

    Claude uses domains_detected to load relevant skills.
    """

@tool
def get_principles(topic: str | None = None) -> str:
    """Load engineering principles/checklists from markdown."""

@tool
def delegate_semgrep(path: str, config: str = "auto") -> Findings:
    """Direct semgrep access."""

@tool
def delegate_ruff(path: str) -> Findings:
    """Direct ruff access (Python)."""

@tool
def delegate_slither(path: str, detectors: list[str] | None = None) -> Findings:
    """Direct slither access (Solidity)."""

@tool
def check_tools() -> ToolStatus:
    """Show which analysis tools are installed."""
```

### What's NOT in MCP

- **Domain detection**: Internal to `quick_review`, not exposed
- **Persona loading**: Handled by Claude via skills
- **Tension detection**: Claude synthesizes naturally
- **Review orchestration**: Claude composes tools + skills

---

## Skills

Installed to `~/.claude/skills/crucible/` via `crucible skills install`.

### Skill Format

```markdown
# security-engineer/SKILL.md
---
triggers: [security, auth, injection, secrets]
always_run: true
---

# Security Engineer

You are reviewing code from a security perspective...

## Key Questions
- What's the threat model?
- What if this input is malicious?

## Red Flags
- Raw user input in queries
- Missing auth checks

## Before Approving
- [ ] Threat model documented
- [ ] Input validated at boundaries
```

### Skill Loading

Claude sees `domains_detected: ["solidity", "smart_contract"]` from MCP, matches to skill triggers, loads relevant perspectives.

### Config Cascade

```
Project > Personal > Package defaults

<project>/.claude/skills/crucible/  # Project overrides
~/.claude/skills/crucible/          # User defaults
<package>/src/crucible/skills/      # Package defaults
```

---

## Data Models

```python
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

@dataclass(frozen=True)
class ToolFinding:
    tool: str           # "slither", "semgrep", "ruff"
    rule: str           # detector/rule name
    severity: Severity
    message: str
    location: str       # file:line
    suggestion: str | None
```

Note: `Persona`, `PersonaReview`, `Tension`, `ReviewResult` dataclasses were removed - Claude handles persona logic via skills.

---

## Tensions

Tensions emerge naturally when Claude loads multiple skills with conflicting guidance:

| Skill | Says |
|-------|------|
| security-engineer | "Add input validation on every field" |
| performance-engineer | "That's 6 extra checks on the hot path" |

Claude identifies the trade-off and surfaces it to the user. No explicit tension detection algorithm needed.

See `docs/FUTURE_ENHANCEMENTS.md` for potential explicit tension modeling if needed.

---

## Directory Structure

```
crucible/
├── src/crucible/
│   ├── server.py           # MCP server (6 tools)
│   ├── cli.py              # crucible skills install/list
│   ├── models.py           # Domain, Severity, ToolFinding
│   ├── domain/
│   │   └── detection.py    # Extension + content detection
│   ├── tools/
│   │   └── delegation.py   # Shell out to analysis tools
│   ├── knowledge/
│   │   └── loader.py       # Load principles markdown
│   └── skills/
│       ├── security-engineer/SKILL.md
│       └── web3-engineer/SKILL.md
├── knowledge/
│   ├── ENGINEERING_PRINCIPLES.md
│   └── SENIOR_ENGINEER_CHECKLIST.md
├── docs/
│   └── FUTURE_ENHANCEMENTS.md
└── tests/
```

---

## Example Flow

```
User: "Review src/Vault.sol"

1. Claude calls quick_review(path="src/Vault.sol")

2. MCP returns:
   {
     "domains_detected": ["solidity", "smart_contract", "web3"],
     "severity_summary": {"high": 2, "medium": 1},
     "findings": [
       {"tool": "slither", "rule": "reentrancy-eth", "severity": "high", ...},
       {"tool": "semgrep", "rule": "unchecked-transfer", "severity": "medium", ...}
     ]
   }

3. Claude sees "smart_contract" → loads web3-engineer skill
   Claude sees "security" always-run → loads security-engineer skill

4. Claude reviews findings through both perspectives:
   - security-engineer: "Reentrancy is critical, block until fixed"
   - web3-engineer: "Use CEI pattern, add ReentrancyGuard"

5. Claude synthesizes:
   "Critical: Reentrancy vulnerability in withdraw().
    Fix: Implement CEI pattern + ReentrancyGuard.
    Both security and web3 perspectives agree this blocks deployment."
```

---

## References

- MCP Protocol: https://modelcontextprotocol.io/
- Slither: https://github.com/crytic/slither
- Semgrep: https://semgrep.dev/
- Ruff: https://docs.astral.sh/ruff/
