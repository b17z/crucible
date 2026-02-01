# Crucible Architecture

How the pieces fit together.

## The Big Picture

Crucible is a Claude Code customization layer. It does two things:

1. **Detects context** → What domain is this code in?
2. **Loads patterns** → Personas (how to think) + Knowledge (what to apply)

Claude uses the domain detection to load relevant personas and knowledge.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOW IT WORKS                                    │
└─────────────────────────────────────────────────────────────────────────────┘

  User: "Work on src/Vault.sol"
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
  │  2. Loads matching personas: web3-engineer, security-engineer            │
  │  3. Personas provide: questions, red flags, checklists                   │
  │  4. Claude thinks like your stack requires                               │
  └─────────────────────────────────────────────────────────────────────────┘
```

---

## MCP Server Entry Points

The server exposes tools via `server.py`:

```
┌─────────────────────────────────────────────────────────────────────┐
│                          MCP TOOLS                                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Main review tool:                                                  │
│  └── review(path?, mode?)     Unified review: path OR git-aware     │
│                               Runs analysis + skills + knowledge +  │
│                               enforcement assertions                 │
│                                                                     │
│  Context injection (call at session start):                         │
│  ├── get_assertions()         Load enforcement rules                │
│  ├── get_principles(topic)    Load engineering knowledge            │
│  └── load_knowledge(files)    Load specific knowledge files         │
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
│  delegate_gitleaks(path, staged_only?)                              │
│    └─→ subprocess: gitleaks detect/protect --json                   │
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

## Skill Matching (full_review)

`full_review` matches skills based on domain and triggers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SKILL MATCHING                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Skill frontmatter options:                                         │
│                                                                     │
│  always_run: true              # Include for all domains            │
│  always_run_for_domains: [X]   # Include if domain matches          │
│  triggers: [keyword1, ...]     # Match against domain_tags          │
│                                                                     │
│  Matching algorithm:                                                │
│                                                                     │
│  1. always_run: true → always include                               │
│     security-engineer runs on all code                              │
│                                                                     │
│  2. always_run_for_domains matches domain → include                 │
│     web3-engineer: always_run_for_domains: [smart_contract]         │
│     gas-optimizer: always_run_for_domains: [smart_contract]         │
│                                                                     │
│  3. triggers intersect domain_tags → include                        │
│     backend-engineer triggers: [api, database, server]              │
│     domain_tags: [python, backend, api] → matches "api"             │
│                                                                     │
│  Returns: skill name + matching triggers for each skill             │
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
├── server.py              # MCP server (10 tools)
├── cli.py                 # crucible commands (skills/knowledge/hooks)
├── models.py              # Domain, Severity, ToolFinding
├── errors.py              # Result types (Ok/Err)
│
├── domain/
│   └── detection.py       # Classify code by extension/content
│
├── tools/
│   ├── delegation.py      # Shell out to analysis tools
│   └── git.py             # Git operations (staged/branch/commits)
│
├── hooks/
│   ├── precommit.py       # Pre-commit hook implementation
│   └── claudecode.py      # Claude Code PostToolUse hook
│
├── knowledge/
│   ├── loader.py          # Load principles with cascade
│   └── principles/        # 14 bundled knowledge files
│       ├── SECURITY.md
│       ├── TESTING.md
│       ├── SMART_CONTRACT.md
│       └── ...
│
├── skills/
│   ├── loader.py          # Skill parsing and matching
│   └── <skill>/SKILL.md   # 18 bundled persona skills
│       ├── security-engineer/
│       ├── web3-engineer/
│       └── ...
│
├── enforcement/
│   ├── assertions.py      # Load/validate YAML assertion files
│   ├── patterns.py        # Pattern matching with suppression
│   ├── compliance.py      # LLM compliance checking
│   ├── budget.py          # Token estimation and tracking
│   ├── models.py          # Assertion, Finding, Config models
│   └── bundled/           # 30 bundled assertions
│       ├── security.yaml
│       ├── error-handling.yaml
│       └── smart-contract.yaml

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

## Git Integration

`tools/git.py` extracts change context for targeted analysis:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      GIT OPERATIONS                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  get_staged_changes(repo)     → Changes ready to commit             │
│  get_unstaged_changes(repo)   → Working directory changes           │
│  get_branch_diff(repo, base)  → Branch vs base (three-dot diff)     │
│  get_recent_commits(repo, n)  → Last N commits                      │
│                                                                     │
│  Returns: GitContext                                                │
│    ├── mode: staged | unstaged | branch | commits                   │
│    ├── base_ref: branch name or HEAD~N                              │
│    ├── changes: list[GitChange]                                     │
│    │     ├── path: file path                                        │
│    │     ├── status: A (added) | M (modified) | D (deleted)         │
│    │     └── added_lines: list[LineRange]  ← for filtering findings │
│    └── commit_messages: for branch/commits mode                     │
│                                                                     │
│  Findings are filtered to only changed lines via added_lines.       │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Pre-commit Hooks

`hooks/precommit.py` implements git hooks with the same patterns:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      PRE-COMMIT FLOW                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Secrets detection (first, fails fast):                          │
│     ├── gitleaks (if installed and configured)                      │
│     └── builtin patterns (fallback)                                 │
│                                                                     │
│  2. Static analysis (domain-aware):                                 │
│     ├── .sol → slither, semgrep                                     │
│     ├── .py  → ruff, bandit, semgrep                                │
│     └── other → semgrep                                             │
│                                                                     │
│  3. Filter to staged lines only                                     │
│                                                                     │
│  4. Check severity threshold                                        │
│                                                                     │
│  Config cascade: .crucible/precommit.yaml > ~/.claude/crucible/     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Claude Code Hooks

`hooks/claudecode.py` integrates with Claude Code's PostToolUse hook:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CLAUDE CODE HOOK FLOW                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Claude calls Edit or Write tool                                 │
│                                                                     │
│  2. Claude Code runs PostToolUse hook:                              │
│     crucible hooks claudecode hook                                  │
│                                                                     │
│  3. Hook receives JSON on stdin:                                    │
│     {"tool_name": "Write", "tool_input": {...}}                     │
│                                                                     │
│  4. Crucible runs pattern assertions against file                   │
│                                                                     │
│  5. Exit codes:                                                     │
│     0 = allow (operation proceeds)                                  │
│     2 = deny (stderr shown to Claude as feedback)                   │
│                                                                     │
│  Config: .crucible/claudecode.yaml                                  │
│     on_finding: deny | warn | allow                                 │
│     severity_threshold: error | warning | info                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

Setup: `crucible hooks claudecode init` generates `.claude/settings.json`.

---

## Enforcement Assertions

`enforcement/` provides pattern and LLM-based code assertions:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ENFORCEMENT FLOW                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Assertions loaded from cascade:                                    │
│    1. .crucible/assertions/*.yaml   (project)                       │
│    2. ~/.claude/crucible/assertions/*.yaml  (user)                  │
│    3. <package>/enforcement/bundled/*.yaml  (bundled)               │
│                                                                     │
│  Two types:                                                         │
│                                                                     │
│  Pattern (fast, free):                                              │
│    - Regex matching against code                                    │
│    - Inline suppression: // crucible-ignore: rule-id                │
│    - Always runs                                                    │
│                                                                     │
│  LLM (semantic, uses API tokens):                                      │
│    - Sends code + compliance prompt to Claude                       │
│    - Token budget controls cost                                     │
│    - Priority sorting (critical first)                              │
│    - Model selection (Sonnet default, Opus for high-stakes)         │
│                                                                     │
│  30 bundled assertions across 3 files:                              │
│    security.yaml       - 12 assertions                              │
│    error-handling.yaml - 8 assertions                               │
│    smart-contract.yaml - 10 assertions                              │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
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
