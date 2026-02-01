# Crucible Knowledge

All 14 bundled engineering knowledge files.

## Overview

Knowledge files are domain-specific engineering principles. They're loaded via:

1. `get_principles(topic)` MCP tool
2. Skill `knowledge:` frontmatter linking

---

## Knowledge Files

### SECURITY.md

Quick reference for secure code patterns.

**Topics covered:**
- Input validation at trust boundaries
- SQL injection prevention (parameterized queries)
- Secrets management (env vars, rotation)
- Defense in depth (prevention → detection → response → recovery)
- Deserialization safety (pickle, yaml.load, eval)
- Risk surface mapping

**Linked by:** security-engineer, protocol-architect, mev-researcher, incident-responder

---

### TESTING.md

What to test, how to structure tests, and patterns that work.

**Topics covered:**
- Test pyramid (unit → integration → E2E)
- What to test vs what not to test
- Pure functions make testing easy
- Test naming conventions
- Integration tests with real behavior
- Property-based testing (fast-check)
- Bug regression workflow

**Linked by:** formal-verification, accessibility-engineer, mobile-engineer

---

### ERROR_HANDLING.md

Result types, typed errors, and when to throw.

**Topics covered:**
- Errors as values, not exceptions
- Result type pattern (Ok/Err)
- Typed errors with exhaustiveness checking
- When to throw (truly exceptional cases)
- Python Result pattern with dataclasses
- Error message best practices
- Never swallow errors

**Linked by:** backend-engineer, product-engineer, mobile-engineer, fde-engineer, customer-success

---

### TYPE_SAFETY.md

Patterns for making invalid states unrepresentable.

**Topics covered:**
- No `any` - use `unknown` + narrowing
- Branded types (PageId, UserId, Cents)
- Discriminated unions for state
- Zod at boundaries
- Exhaustiveness checking with `never`
- Strict mode settings
- Optional vs required clarity

**Linked by:** data-engineer, uiux-engineer

---

### API_DESIGN.md

REST conventions, response shapes, and common patterns.

**Topics covered:**
- REST conventions (nouns not verbs)
- Consistent response shapes
- HTTP status codes reference
- Rate limiting headers
- Pagination patterns
- API versioning strategies
- Idempotency keys
- Error response structure
- tRPC for internal APIs

**Linked by:** backend-engineer, product-engineer, fde-engineer

---

### DATABASE.md

Indexes, N+1 queries, transactions, and migrations.

**Topics covered:**
- Core rules (UUIDs, timestamps, soft delete, amounts in cents)
- Index strategy (FKs, WHERE, ORDER BY, composite)
- Optimization order
- N+1 query prevention
- Naming conventions
- Migration best practices
- Transaction usage
- Connection pooling
- Query safety (parameterized)

**Linked by:** backend-engineer, performance-engineer, data-engineer

---

### SYSTEM_DESIGN.md

Monolith first, stateless, queues, and caching strategies.

**Topics covered:**
- Start monolith, earn microservices
- The boring architecture
- Stateless by default
- Horizontal vs vertical scaling
- Queue everything that can wait
- Cache strategically
- Idempotency patterns
- Fail gracefully (timeouts, retries, circuit breakers)

**Linked by:** performance-engineer, devops-engineer, tech-lead

---

### OBSERVABILITY.md

Logs, metrics, traces, and alerting patterns.

**Topics covered:**
- The triad: logs, metrics, traces
- Minimum viable observability
- Structured logging (JSON, not strings)
- Log levels (ERROR, WARN, INFO, DEBUG)
- Health check endpoints
- Metrics to track (RED method)
- Alerting on SLOs
- Correlation IDs
- Observability budget for features

**Linked by:** performance-engineer, devops-engineer, incident-responder

---

### SMART_CONTRACT.md

CEI pattern, gas optimization, and common vulnerabilities.

**Topics covered:**
- EVM cost model vs traditional backend
- Quick checklist (CEI, reentrancy, tx.origin, etc.)
- CEI pattern (Checks-Effects-Interactions)
- State optimization (constant, immutable, storage)
- Common vulnerabilities (reentrancy, tx.origin, unchecked returns)
- Security invariants
- Gas optimization (cache storage, loop patterns)
- Anti-patterns (premature upgradeability, deep inheritance)

**Linked by:** web3-engineer, gas-optimizer, protocol-architect, mev-researcher, formal-verification

---

### FP.md

Pure functions, immutability, and composition patterns.

**Topics covered:**
- Core philosophy (default to FP)
- Pure functions (same input → same output)
- Immutability patterns
- Composition over inheritance
- Functions vs classes
- Data transformations (pipelines over loops)
- Side effects at the edges

**Note:** Opinionated template favoring FP patterns.

---

### COMMITS.md

Semantic commit messages and atomic commits.

**Topics covered:**
- Commit message format: `(type): description`
- Type reference (feat, fix, docs, refactor, test, chore)
- Good vs bad commit message examples
- Commit body for context
- Atomic commits
- Squashing workflow

---

### DOCUMENTATION.md

FEATURES, ROADMAP, ARCHITECTURE patterns.

**Topics covered:**
- The docs folder structure
- FEATURES.md format
- ROADMAP.md format
- ARCHITECTURE.md format
- Design docs for decisions
- README.md (quick start only)
- CLAUDE.md (AI context)
- Keeping docs current

**Linked by:** tech-lead, fde-engineer, customer-success

---

### GITIGNORE.md

Defense-in-depth patterns for preventing secret commits.

**Topics covered:**
- Structured organization by category
- Environment files (.env, .envrc)
- Private keys and certificates
- Credentials and cloud configs
- Paranoid mode catch-all patterns (*secret*, *password*, *credential*)
- OS and editor files
- Dependencies by language
- Build and test outputs
- Tool-specific ignores (Terraform, Docker, Kubernetes)

**Linked by:** security-engineer, devops-engineer

---

### PRECOMMIT.md

Automated guardrails before code enters the repo.

**Topics covered:**
- Pre-commit framework setup
- Multi-layer secret detection (gitleaks, detect-secrets, custom)
- High-confidence secret patterns (AWS, GitHub, OpenAI, Anthropic)
- Python hooks (ruff, mypy)
- File hygiene hooks
- Commit message validation
- CI integration
- Skip patterns for lock files
- Blocked commit response handling

**Linked by:** security-engineer, devops-engineer

---

## Topic Mapping

The `get_principles(topic)` tool maps topics to files:

| Topic | Files Loaded |
|-------|--------------|
| `security` | SECURITY.md, GITIGNORE.md, PRECOMMIT.md |
| `smart_contract` | SMART_CONTRACT.md |
| `engineering` | TESTING.md, ERROR_HANDLING.md, TYPE_SAFETY.md |
| `checklist` | SECURITY.md, TESTING.md, ERROR_HANDLING.md |
| `repo_hygiene` | GITIGNORE.md, PRECOMMIT.md, COMMITS.md |
| (default) | SECURITY.md, TESTING.md |

---

## Skill → Knowledge Mapping

| Skill | Knowledge Files |
|-------|-----------------|
| security-engineer | SECURITY.md |
| web3-engineer | SECURITY.md, SMART_CONTRACT.md |
| backend-engineer | API_DESIGN.md, DATABASE.md, ERROR_HANDLING.md |
| performance-engineer | SYSTEM_DESIGN.md, DATABASE.md, OBSERVABILITY.md |
| devops-engineer | OBSERVABILITY.md, SYSTEM_DESIGN.md |
| data-engineer | DATABASE.md, TYPE_SAFETY.md |
| tech-lead | DOCUMENTATION.md, SYSTEM_DESIGN.md |
| product-engineer | API_DESIGN.md, ERROR_HANDLING.md |
| accessibility-engineer | TESTING.md |
| mobile-engineer | ERROR_HANDLING.md, TESTING.md |
| uiux-engineer | TYPE_SAFETY.md |
| fde-engineer | API_DESIGN.md, DOCUMENTATION.md, ERROR_HANDLING.md |
| customer-success | DOCUMENTATION.md, ERROR_HANDLING.md |
| gas-optimizer | SMART_CONTRACT.md |
| protocol-architect | SMART_CONTRACT.md, SECURITY.md |
| mev-researcher | SMART_CONTRACT.md, SECURITY.md |
| formal-verification | SMART_CONTRACT.md, TESTING.md |
| incident-responder | OBSERVABILITY.md, SECURITY.md |

---

## Knowledge → Assertion Linking

Knowledge files can link to assertion files via frontmatter:

```yaml
---
name: Security Principles
description: Core security principles
triggers: [security, auth, crypto]
type: principle
assertions: security.yaml
---
```

**Bundled links:**

| Knowledge | Assertion File |
|-----------|----------------|
| SECURITY.md | security.yaml |
| ERROR_HANDLING.md | error-handling.yaml |
| SMART_CONTRACT.md | smart-contract.yaml |

When these knowledge files are loaded, their linked assertions are also available.

---

## Customization

See [CUSTOMIZATION.md](CUSTOMIZATION.md) for how to:
- Override bundled knowledge for your project
- Add project-specific knowledge files
- Link custom knowledge to skills
- Link knowledge to assertion files
