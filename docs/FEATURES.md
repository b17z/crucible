# Crucible Features

Complete reference for all Crucible capabilities.

## Overview

```
├── Enforcement:   Pattern + LLM assertions that block bad code
├── Personas:      Domain-specific thinking (how to approach problems)
├── Knowledge:     Coding patterns and principles (what to apply)
├── Cascade:       Project → User → Bundled (customizable at every level)
└── Context-aware: Loads relevant skills based on what you're working on
```

**Enforcement, not just context. Your patterns block bad code automatically.**

---

## Enforcement

Crucible enforces your patterns through hooks that run automatically.

### Bundled Assertions

30 assertions across 3 files:

| File | Assertions | Covers |
|------|------------|--------|
| `security.yaml` | 12 | eval, exec, shell injection, pickle, secrets, SQL, weak crypto |
| `error-handling.yaml` | 8 | bare except, silent catch, empty catch, error suppression |
| `smart-contract.yaml` | 10 | reentrancy, CEI, access control, tx.origin, overflow, DoS |

### Assertion Types

**Pattern assertions** (fast, free):
```yaml
- id: no-eval
  type: pattern
  pattern: "\\beval\\s*\\("
  message: "eval() is dangerous"
  severity: error
  priority: critical
  languages: [python]
```

**LLM assertions** (semantic, uses API tokens):
```yaml
- id: error-handling-check
  type: llm
  compliance: |
    Check that error handling follows best practices:
    1. Errors are not silently swallowed
    2. Error messages are descriptive
  message: "Error handling may need improvement"
  severity: warning
  priority: medium
  model: sonnet  # or opus for high-stakes
```

### Hooks

**Pre-commit hook** (`crucible hooks install`):
- Runs on every `git commit`
- Checks secrets, static analysis, pattern assertions
- Fails commit if high+ severity findings

**Claude Code hook** (`crucible hooks claudecode init`):
- Runs on every `Edit` or `Write` operation
- Zero context cost (runs outside Claude's context)
- Exit code 2 blocks the operation and shows feedback to Claude

### Configuration

`.crucible/precommit.yaml`:
```yaml
fail_on: high
run_assertions: true
run_llm_assertions: false  # Off by default (slow)
llm_token_budget: 5000
exclude:
  - "*.md"
```

`.crucible/claudecode.yaml`:
```yaml
on_finding: deny           # deny, warn, allow
severity_threshold: error  # error, warning, info
run_assertions: true
run_llm_assertions: false
exclude:
  - "**/*.md"
  - "**/test_*.py"
```

---

## MCP Tools

### review(path?, mode?, ...)

Unified code review tool. Supports path-based review OR git-aware review.

```
review(path="src/Vault.sol")

→ Domains: solidity, smart_contract, web3
→ Severity summary: {critical: 1, high: 3, medium: 5}
→ Matched skills, knowledge loaded, static analysis + enforcement findings
```

**Auto-detected tools by domain:**

| Domain | Tools Run |
|--------|-----------|
| Smart Contract (.sol, .vy) | slither, semgrep |
| Python (.py) | ruff, bandit, semgrep |
| Frontend (.ts, .tsx, .js) | semgrep |
| Other | semgrep |

**Git-aware review:**

```
review(mode="staged")         # Review staged changes before commit
review(mode="branch")         # Review current branch vs main
review(mode="commits", base="3")  # Review last 3 commits
```

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `path` | File or directory to review |
| `mode` | Git mode: staged, unstaged, branch, commits |
| `base` | Base branch for branch mode, or count for commits mode |
| `include_context` | Include findings within 5 lines of changes |
| `skills` | Override auto skill selection |
| `include_skills` | Load skills/checklists (default: true) |
| `include_knowledge` | Load knowledge files (default: true) |
| `enforce` | Run pattern assertions (default: true) |
| `compliance_enabled` | Run LLM assertions (default: true) |
| `compliance_model` | Model for LLM assertions: sonnet, opus, haiku |
| `token_budget` | Token budget for LLM assertions |

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

### get_assertions(include_compliance?)

Load active enforcement assertions for context injection at session start.

```
get_assertions()

→ # Active Enforcement Assertions
→ These patterns are enforced during code review. Avoid these in your code.
→
→ ## Pattern Assertions (fast, always run)
→ | ID | Message | Severity | Languages |
→ | no-eval | eval() is dangerous | error | python |
→ | no-bare-except | Catch specific exceptions | warning | python |
→ ...
```

Call this at session start so Claude knows what patterns to avoid *before* writing code.

### load_knowledge(files?, topic?, include_bundled?)

Load knowledge/principles files without running static analysis. Loads all 14 bundled knowledge files by default.

```
load_knowledge()
→ All 14 bundled knowledge files (project/user files override)

load_knowledge(topic="security")
→ SECURITY.md content

load_knowledge(files=["API_DESIGN.md", "DATABASE.md"])
→ Combined content from specified files
```

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `files` | Specific files to load (e.g., `["SECURITY.md"]`) |
| `topic` | Load by topic: security, engineering, smart_contract, checklist, repo_hygiene |
| `include_bundled` | Include bundled files (default: true). Project/user files override bundled. |

### delegate_* Tools

Direct access to individual analysis tools:

| Tool | Purpose |
|------|---------|
| `delegate_semgrep(path, config?)` | Run semgrep with custom config |
| `delegate_ruff(path)` | Python linting |
| `delegate_slither(path, detectors?)` | Solidity analysis |
| `delegate_bandit(path)` | Python security |
| `delegate_gitleaks(path, staged_only?)` | Secrets detection |

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

### 14 Domain Files

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
| **GITIGNORE.md** | Defense-in-depth patterns for preventing secret commits |
| **PRECOMMIT.md** | Automated guardrails before code enters the repo |

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

### Git Hooks

```bash
crucible hooks install [path]     # Install pre-commit hook
crucible hooks install --force    # Replace existing hook
crucible hooks uninstall [path]   # Remove pre-commit hook
crucible hooks status [path]      # Show hook installation status
```

### Claude Code Hooks

```bash
crucible hooks claudecode init    # Initialize Claude Code hooks
crucible hooks claudecode hook    # Run hook (called by Claude Code)
```

This creates:
- `.claude/settings.json` with PostToolUse hook for Edit|Write
- `.crucible/claudecode.yaml` for configuration

### Assertions Management

```bash
crucible assertions list          # List all assertion files
crucible assertions validate      # Validate assertion files
crucible assertions test file.py  # Test assertions against a file
crucible assertions explain <id>  # Explain what a rule does
crucible assertions debug         # Debug applicability for a rule
```

### Code Review

```bash
crucible review                   # Review staged changes (default)
crucible review --mode unstaged   # Review working directory changes
crucible review --mode branch     # Review current branch vs main
crucible review --mode commits    # Review last commit
crucible review --base develop    # Use different base branch
crucible review --fail-on medium  # Exit non-zero if findings >= severity
crucible review --include-context # Include findings near changes
crucible review --json            # Output as JSON
crucible review --format report   # Output as markdown audit report
crucible review --quiet           # Suppress progress output
crucible review src/file.py --no-git  # Review without git awareness

# Generate a markdown report file
crucible review --format report > review-report.md
```

**Modes:**

| Mode | Description |
|------|-------------|
| `staged` | Changes ready to commit (default) |
| `unstaged` | Working directory changes |
| `branch` | Current branch vs base |
| `commits` | Recent N commits |

**Configuration:**

Create `.crucible/review.yaml` or `~/.claude/crucible/review.yaml`:

```yaml
# Default fail threshold
fail_on: high

# Per-domain overrides (stricter for smart contracts)
fail_on_domain:
  smart_contract: critical
  backend: high

# Skip specific tools
skip_tools:
  - slither  # Skip if slow

# Include findings near changes
include_context: false
```

CLI arguments override config file values.

### Pre-commit Check

```bash
crucible pre-commit [path]        # Run checks on staged changes
crucible pre-commit --fail-on medium  # Set severity threshold
crucible pre-commit --verbose     # Show all findings
crucible pre-commit --json        # Output as JSON
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

## Pre-commit Hooks

Crucible can install a git pre-commit hook that runs before each commit.

### What It Checks

1. **Secrets detection** - Blocks commits containing sensitive files
2. **Static analysis** - Domain-aware tool selection on staged changes

### Installation

```bash
crucible hooks install
```

### Configuration

Create `.crucible/precommit.yaml`:

```yaml
# Fail on findings at or above this severity
fail_on: high  # critical, high, medium, low, info

# Secrets detection tool
secrets_tool: auto  # auto, gitleaks, builtin, none

# File patterns to exclude from static analysis
exclude:
  - "*.md"
  - "tests/**"

# Skip specific tools
skip_tools:
  - slither  # Skip if too slow

# Per-domain tool overrides
tools:
  smart_contract: [semgrep]  # Skip slither
  python: [ruff, semgrep]    # Skip bandit
```

### Secrets Detection Options

| Value | Behavior |
|-------|----------|
| `auto` | Use gitleaks if installed, else builtin (default) |
| `gitleaks` | Use gitleaks only |
| `builtin` | Use crucible's pattern matching |
| `none` | Disable secrets detection |

The builtin detector catches: `.env` files, private keys (`.pem`, `.key`), SSH keys, keystores, credentials JSON, and more.

---

## Ignore Patterns

Crucible uses `.crucibleignore` files (gitignore syntax) to exclude files from review.

### Default Patterns

49 built-in patterns exclude common non-source directories:
- `node_modules/`, `.pnpm/`, `vendor/`
- `.next/`, `.nuxt/`, `dist/`, `build/`
- `.git/`, `__pycache__/`, `.venv/`
- `package-lock.json`, `yarn.lock`, `*.log`

### CLI Commands

```bash
crucible ignore show              # Show all active patterns
crucible ignore init              # Create .crucible/.crucibleignore
crucible ignore test <path>       # Test if a path would be ignored
```

### Custom Patterns

Create `.crucible/.crucibleignore` for project-specific exclusions:

```gitignore
# Project-specific ignores (in addition to defaults)
generated/
fixtures/large-*.json
```

### Cascade Resolution

```
1. .crucible/.crucibleignore          # Project (highest)
2. ~/.claude/crucible/.crucibleignore # User
3. Built-in defaults                   # (lowest)
```

All patterns are combined. Use `!pattern` to un-ignore.

---

## External Tools

Crucible shells out to these (install separately):

```bash
pip install semgrep           # Multi-language patterns (required)
pip install ruff              # Python linting (required for Python)
pip install slither-analyzer  # Solidity analysis (for .sol files)
pip install bandit            # Python security (optional, enhances Python review)
```

For secrets detection:

```bash
# macOS
brew install gitleaks

# or from releases
# https://github.com/gitleaks/gitleaks/releases
```

Use `check_tools()` to verify installation status.
