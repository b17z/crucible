# Crucible Features

Complete reference for all Crucible capabilities.

## Overview

```
├── Personas:      Domain-specific thinking (how to approach problems)
├── Knowledge:     Coding patterns and principles (what to apply)
├── Cascade:       Project → User → Bundled (customizable at every level)
└── Context-aware: Loads relevant skills based on what you're working on
```

**Personas for domains. Knowledge for patterns. All customizable.**

---

## MCP Tools

### quick_review(path)

Run static analysis and return findings with domain metadata.

```
quick_review(path="src/Vault.sol")

→ domains_detected: solidity, smart_contract, web3
→ severity_summary: {critical: 1, high: 3, medium: 5}
→ Semgrep findings, Slither findings
```

Claude sees the domain metadata and loads relevant skills (web3-engineer, security-engineer).

**Auto-detected tools by domain:**

| Domain | Tools Run |
|--------|-----------|
| Smart Contract (.sol, .vy) | slither, semgrep |
| Python (.py) | ruff, bandit, semgrep |
| Frontend (.ts, .tsx, .js) | semgrep |
| Other | semgrep |

### get_principles(topic?)

Load domain-specific engineering knowledge.

```
get_principles(topic="security")
→ Security principles, checklists, patterns

get_principles(topic="smart_contract")
→ CEI pattern, gas optimization, vulnerabilities
```

**Available topics:**
- `security` - SECURITY.md
- `smart_contract` - SMART_CONTRACT.md
- `engineering` - TESTING.md, ERROR_HANDLING.md, TYPE_SAFETY.md
- `checklist` - Combined security + testing + error handling

### delegate_* Tools

Direct access to individual analysis tools:

| Tool | Purpose |
|------|---------|
| `delegate_semgrep(path, config?)` | Run semgrep with custom config |
| `delegate_ruff(path)` | Python linting |
| `delegate_slither(path, detectors?)` | Solidity analysis |
| `delegate_bandit(path)` | Python security |

### check_tools()

Show which analysis tools are installed.

```
check_tools()

→ semgrep: ✅ Installed (1.56.0)
→ ruff: ✅ Installed (0.4.1)
→ slither: ❌ Not found
→ bandit: ✅ Installed (1.7.7)
```

---

## Personas

Domain-specific thinking that Claude loads based on what you're working on.

### 18 Bundled Personas

| Skill | Triggers | Focus |
|-------|----------|-------|
| **security-engineer** | auth, secrets, injection | Threat models, input validation, OWASP |
| **web3-engineer** | solidity, smart_contract | Reentrancy, CEI, gas, access control |
| **backend-engineer** | api, database, server | N+1, timeouts, idempotency |
| **performance-engineer** | latency, optimization | Hot paths, caching, complexity |
| **devops-engineer** | docker, kubernetes, ci/cd | Health checks, observability |
| **data-engineer** | database, migration, schema | Indexes, migrations, integrity |
| **tech-lead** | architecture, refactor | Abstractions, tech debt, shipping |
| **product-engineer** | feature, user, metrics | Success metrics, error states |
| **accessibility-engineer** | a11y, wcag, aria | Keyboard, screen reader, contrast |
| **mobile-engineer** | ios, android, flutter | Offline, bundle size, platform |
| **uiux-engineer** | design, component, css | Design system, states, responsive |
| **fde-engineer** | integration, sdk, customer | Configurability, troubleshooting |
| **customer-success** | support, error message | Supportability, actionable errors |
| **gas-optimizer** | gas, storage, calldata | Storage caching, struct packing |
| **protocol-architect** | defi, governance, proxy | Economic security, upgrade paths |
| **mev-researcher** | frontrun, sandwich, flash | Slippage, manipulation, TWAP |
| **formal-verification** | invariant, proof, certora | Invariants, specifications |
| **incident-responder** | outage, recovery, rollback | Kill switches, blast radius |

### Skill Resolution Cascade

Skills are loaded with priority (first found wins):

```
1. .crucible/skills/<skill>/SKILL.md   # Project (highest)
2. ~/.claude/crucible/skills/<skill>/  # User
3. <package>/skills/<skill>/           # Bundled (lowest)
```

### Skill → Knowledge Linking

Each skill declares what knowledge it needs via frontmatter:

```yaml
# web3-engineer/SKILL.md
---
version: "1.0"
triggers: [solidity, smart_contract, web3]
knowledge: [SECURITY.md, SMART_CONTRACT.md]
---
```

When the skill loads, linked knowledge is available via `get_principles()`.

---

## Knowledge

Engineering principles organized by domain.

### 12 Domain Files

| File | Content |
|------|---------|
| **SECURITY.md** | Input validation, secrets, defense in depth |
| **TESTING.md** | Test pyramid, what to test, property testing |
| **ERROR_HANDLING.md** | Result types, typed errors, when to throw |
| **TYPE_SAFETY.md** | Branded types, discriminated unions, Zod |
| **API_DESIGN.md** | REST, pagination, rate limiting, idempotency |
| **DATABASE.md** | Indexes, N+1, transactions, migrations |
| **SYSTEM_DESIGN.md** | Monolith first, stateless, queues, caching |
| **OBSERVABILITY.md** | Logs, metrics, traces, alerting |
| **SMART_CONTRACT.md** | CEI pattern, gas, reentrancy, invariants |
| **FP.md** | Pure functions, immutability, composition |
| **COMMITS.md** | Semantic commit messages, atomic commits |
| **DOCUMENTATION.md** | FEATURES, ROADMAP, ARCHITECTURE patterns |

### Knowledge Resolution Cascade

Same pattern as skills:

```
1. .crucible/knowledge/<file>.md   # Project (highest)
2. ~/.claude/crucible/knowledge/   # User
3. <package>/knowledge/principles/ # Bundled (lowest)
```

---

## CLI Commands

### Skills Management

```bash
crucible skills list              # List all skills from all sources
crucible skills install           # Install to ~/.claude/crucible/skills/
crucible skills init <skill>      # Copy to .crucible/skills/ for customization
crucible skills show <skill>      # Show resolution cascade
```

### Knowledge Management

```bash
crucible knowledge list           # List all knowledge files
crucible knowledge install        # Install to ~/.claude/crucible/knowledge/
crucible knowledge init <file>    # Copy to .crucible/knowledge/
crucible knowledge show <file>    # Show resolution cascade
```

### MCP Server

```bash
crucible-mcp                      # Run as MCP server
```

---

## Customization

### Project-Level Skills

Override a skill for your project:

```bash
crucible skills init security-engineer
# Creates .crucible/skills/security-engineer/SKILL.md

# Edit to add project-specific concerns:
# - Internal auth patterns
# - Team conventions
# - Domain-specific threats
```

### Project-Level Knowledge

Override knowledge for your project:

```bash
crucible knowledge init SECURITY
# Creates .crucible/knowledge/SECURITY.md

# Edit to add:
# - Company security policies
# - Internal tooling references
# - Project-specific patterns
```

### Creating New Skills

```bash
mkdir -p .crucible/skills/my-skill
```

```yaml
# .crucible/skills/my-skill/SKILL.md
---
version: "1.0"
triggers: [keyword1, keyword2]
knowledge: [RELEVANT.md]
---

# My Custom Skill

Review focus and key questions...

## Red Flags
- Pattern 1
- Pattern 2

## Before Approving
- [ ] Checklist item 1
- [ ] Checklist item 2
```

---

## External Tools

Crucible shells out to these (install separately):

```bash
pip install semgrep           # Multi-language patterns (required)
pip install ruff              # Python linting (required for Python)
pip install slither-analyzer  # Solidity analysis (for .sol files)
pip install bandit            # Python security (optional, enhances Python review)
```

Use `check_tools()` to verify installation status.
