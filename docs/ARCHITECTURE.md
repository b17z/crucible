# Crucible Architecture

How the pieces fit together.

## The Big Picture

Crucible is an MCP server that helps Claude review code. It does two things:

1. **Runs static analysis** → Returns findings with domain metadata
2. **Provides engineering knowledge** → Skills (personas) + principles

Claude uses the domain metadata to load relevant skills, then synthesizes a multi-perspective review.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              REVIEW FLOW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

  User: "Review src/Vault.sol"
           │
           ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  Claude calls quick_review(path="src/Vault.sol")                         │
  └───────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  CRUCIBLE MCP SERVER                                                     │
  │                                                                          │
  │  1. Domain detection: .sol → smart_contract                              │
  │  2. Tool selection: slither, semgrep (based on domain)                   │
  │  3. Run tools, collect findings                                          │
  │  4. Return: {domains: [...], severity: {...}, findings: [...]}           │
  └───────────────────────────────────┬─────────────────────────────────────┘
                                      │
                                      ▼
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  CLAUDE                                                                  │
  │                                                                          │
  │  1. Sees domains: ["smart_contract", "web3"]                             │
  │  2. Loads skills matching triggers: web3-engineer, security-engineer     │
  │  3. Skills provide: questions, red flags, checklists                     │
  │  4. Synthesizes multi-perspective review                                 │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Server Entry Points

The server exposes 7 tools via `server.py`:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MCP TOOLS                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Main tools:                                                        │
│  ├── quick_review(path)       Run analysis, return findings + domains │
│  └── get_principles(topic)    Load engineering knowledge            │
│                                                                     │
│  Direct tool access:                                                │
│  ├── delegate_semgrep(path)   Multi-language patterns               │
│  ├── delegate_ruff(path)      Python linting                        │
│  ├── delegate_slither(path)   Solidity analysis                     │
│  └── delegate_bandit(path)    Python security                       │
│                                                                     │
│  Utility:                                                           │
│  └── check_tools()            Show installed analysis tools         │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Tool Delegation Flow

`tools/delegation.py` shells out to external tools and normalizes output:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TOOL DELEGATION                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Input: file path                                                   │
│                                                                     │
│  delegate_semgrep(path)                                             │
│    └─→ subprocess: semgrep --json --config {config} {path}          │
│        └─→ parse JSON, map to ToolFinding[]                         │
│                                                                     │
│  delegate_ruff(path)                                                │
│    └─→ subprocess: ruff check --output-format=json {path}           │
│        └─→ parse JSON, map to ToolFinding[]                         │
│                                                                     │
│  delegate_slither(path)                                             │
│    └─→ subprocess: slither --json - {path}                          │
│        └─→ parse JSON, map to ToolFinding[]                         │
│                                                                     │
│  delegate_bandit(path)                                              │
│    └─→ subprocess: bandit -f json {path}                            │
│        └─→ parse JSON, map to ToolFinding[]                         │
│                                                                     │
│  Output: Result[list[ToolFinding], str]                             │
│                                                                     │
│  ToolFinding = {tool, rule, severity, message, location, suggestion}│
│  Severity normalized to: critical, high, medium, low, info          │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Domain Detection

`domain/detection.py` classifies code to select tools and skills:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      DOMAIN DETECTION                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Extension-based (fast, primary):                                │
│                                                                     │
│     .sol, .vy    → SMART_CONTRACT  ["solidity", "smart_contract"]   │
│     .py          → BACKEND         ["python", "backend"]            │
│     .ts, .tsx    → FRONTEND        ["typescript", "frontend"]       │
│     .js, .jsx    → FRONTEND        ["javascript", "frontend"]       │
│     .go          → BACKEND         ["go", "backend"]                │
│     .rs          → BACKEND         ["rust", "backend"]              │
│     .tf, .yaml   → INFRASTRUCTURE  ["infrastructure", "devops"]     │
│                                                                     │
│  2. Content-based (fallback):                                       │
│                                                                     │
│     "pragma solidity"   → SMART_CONTRACT                            │
│     "@openzeppelin"     → SMART_CONTRACT                            │
│     "from fastapi"      → BACKEND                                   │
│     "import React"      → FRONTEND                                  │
│     "resource \"aws_"   → INFRASTRUCTURE                            │
│                                                                     │
│  Returns: (Domain, domain_tags: list[str])                          │
│                                                                     │
│  Domain → Tools mapping in quick_review():                          │
│     SMART_CONTRACT → slither, semgrep                               │
│     BACKEND+python → ruff, bandit, semgrep                          │
│     FRONTEND       → semgrep                                        │
│     other          → semgrep                                        │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Skill Resolution Cascade

Skills are loaded from multiple sources with priority:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SKILL RESOLUTION                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Looking for: security-engineer                                     │
│                                                                     │
│  1. PROJECT (highest priority):                                     │
│     .crucible/skills/security-engineer/SKILL.md                     │
│     → Custom for this project                                       │
│                                                                     │
│  2. USER:                                                           │
│     ~/.claude/crucible/skills/security-engineer/SKILL.md            │
│     → Your personal customizations                                  │
│                                                                     │
│  3. BUNDLED (lowest priority):                                      │
│     <package>/skills/security-engineer/SKILL.md                     │
│     → Ships with crucible                                           │
│                                                                     │
│  First found wins.                                                  │
│                                                                     │
│  CLI commands:                                                      │
│     crucible skills list         # See all sources                  │
│     crucible skills show <name>  # See which file is active         │
│     crucible skills init <name>  # Copy to project for customization│
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Knowledge Loading + Linking

Knowledge follows the same cascade, linked via skill frontmatter:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    KNOWLEDGE SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Skill frontmatter declares dependencies:                           │
│                                                                     │
│  # web3-engineer/SKILL.md                                           │
│  ---                                                                │
│  triggers: [solidity, smart_contract]                               │
│  knowledge: [SECURITY.md, SMART_CONTRACT.md]  ← linked knowledge    │
│  ---                                                                │
│                                                                     │
│  Knowledge resolution (same cascade as skills):                     │
│                                                                     │
│  1. .crucible/knowledge/SECURITY.md        # Project                │
│  2. ~/.claude/crucible/knowledge/SECURITY.md  # User                │
│  3. <package>/knowledge/principles/SECURITY.md  # Bundled           │
│                                                                     │
│  get_principles(topic) loads by topic:                              │
│                                                                     │
│  "security"       → SECURITY.md                                     │
│  "smart_contract" → SMART_CONTRACT.md                               │
│  "engineering"    → TESTING.md, ERROR_HANDLING.md, TYPE_SAFETY.md   │
│  "checklist"      → SECURITY.md, TESTING.md, ERROR_HANDLING.md      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
src/crucible/
├── server.py              # MCP server (7 tools)
├── cli.py                 # crucible skills/knowledge commands
├── models.py              # Domain, Severity, ToolFinding
├── errors.py              # Result types (Ok/Err)
│
├── domain/
│   └── detection.py       # Classify code by extension/content
│
├── tools/
│   └── delegation.py      # Shell out to analysis tools
│
├── knowledge/
│   ├── loader.py          # Load principles with cascade
│   └── principles/        # 12 bundled knowledge files
│       ├── SECURITY.md
│       ├── TESTING.md
│       ├── SMART_CONTRACT.md
│       └── ...
│
└── skills/                # 18 bundled persona skills
    ├── security-engineer/SKILL.md
    ├── web3-engineer/SKILL.md
    └── ...

docs/
├── README.md              # Quick start
├── ARCHITECTURE.md        # This document
├── CUSTOMIZATION.md       # Skills + knowledge cascade
├── SKILLS.md              # All 18 personas
├── KNOWLEDGE.md           # All 12 files
└── CONTRIBUTING.md        # For contributors
```

---

## Data Models

```python
# models.py

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
    tool: str           # "semgrep", "ruff", "slither", "bandit"
    rule: str           # Rule ID
    severity: Severity  # Normalized severity
    message: str        # Human-readable description
    location: str       # file:line
    suggestion: str | None
```

---

## Error Handling

Result types for explicit error handling:

```python
# errors.py

from crucible.errors import Result, ok, err

def delegate_semgrep(path: str) -> Result[list[ToolFinding], str]:
    if not tool_installed("semgrep"):
        return err("semgrep not installed")

    findings = run_semgrep(path)
    return ok(findings)

# Caller must handle both cases
result = delegate_semgrep(path)
if result.is_ok:
    findings = result.value
else:
    error_msg = result.error
```

---

## Design Decisions

**Why MCP instead of direct integration?**
- MCP is Claude's standard for tool integration
- Works with Claude Code, Claude Desktop, and agents
- Separation of concerns: Crucible provides data, Claude reasons

**Why shell out to tools instead of Python libraries?**
- Tools have their own release cycles
- Users can update tools independently
- Consistent output format across versions

**Why cascade resolution for skills/knowledge?**
- Project needs override defaults
- User preferences without forking
- Bundled templates as starting point

**Why domain detection?**
- Auto-select appropriate tools
- Auto-load relevant skills via triggers
- No manual configuration per file type
