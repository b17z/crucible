# Crucible Personas

All 20 bundled personas.

## Overview

Personas are domain-specific thinking that Claude loads based on context. Each persona provides:

- **Key Questions** - What to ask about the code
- **Red Flags** - Patterns that indicate problems
- **Before Approving** - Checklist for approval
- **Output Format** - How to structure the review

---

## Skill Reference

### security-engineer

**Triggers:** `auth`, `authentication`, `authorization`, `secrets`, `vulnerability`, `injection`, `xss`, `csrf`, `owasp`

**Always runs:** Yes (on all code)

**Knowledge:** SECURITY.md

**Focus:** Threat models, input validation, defense in depth.

**Key questions:**
- What's the threat model?
- What if this input is malicious?
- Who can access this? Who shouldn't?
- What's logged? What shouldn't be?

---

### web3-engineer

**Triggers:** `solidity`, `smart_contract`, `web3`, `ethereum`, `evm`, `defi`, `vyper`, `foundry`, `hardhat`, `blockchain`

**Always runs for:** `smart_contract` domain

**Knowledge:** SECURITY.md, SMART_CONTRACT.md

**Focus:** Reentrancy, CEI pattern, gas costs, immutability.

**Key questions:**
- Is the address checksummed?
- What if this transaction reverts?
- Is there reentrancy risk?
- What's the MEV exposure?

---

### backend-engineer

**Triggers:** `backend`, `api`, `server`, `database`, `postgres`, `mysql`, `redis`, `queue`, `microservice`, `rest`, `graphql`

**Knowledge:** API_DESIGN.md, DATABASE.md, ERROR_HANDLING.md

**Focus:** Reliability, scalability, operational excellence.

**Key questions:**
- What happens at 10x load?
- Is this idempotent?
- What's the failure mode?
- How do we debug this in production?

---

### performance-engineer

**Triggers:** `performance`, `optimization`, `latency`, `throughput`, `profiling`, `caching`, `slow`, `benchmark`

**Knowledge:** SYSTEM_DESIGN.md, DATABASE.md, OBSERVABILITY.md

**Focus:** Hot paths, complexity, resource efficiency.

**Key questions:**
- What's the hot path?
- What's the time complexity?
- Where's the cache? Should there be one?
- What's blocking the event loop?

---

### devops-engineer

**Triggers:** `devops`, `infrastructure`, `deployment`, `ci`, `cd`, `docker`, `kubernetes`, `terraform`, `aws`, `gcp`, `azure`, `monitoring`, `observability`

**Knowledge:** OBSERVABILITY.md, SYSTEM_DESIGN.md

**Focus:** Operability, observability, incident readiness.

**Key questions:**
- How do we know it's working?
- What alerts should fire when it breaks?
- How do we deploy this safely?
- How do we roll back?

---

### data-engineer

**Triggers:** `data`, `database`, `schema`, `migration`, `etl`, `pipeline`, `sql`, `analytics`, `warehouse`

**Knowledge:** DATABASE.md, TYPE_SAFETY.md

**Focus:** Data integrity, schema design, safe migrations.

**Key questions:**
- What's the source of truth?
- Is this migration reversible?
- What happens to existing data?
- Are there consistency guarantees?

---

### tech-lead

**Triggers:** `architecture`, `design`, `tradeoff`, `abstraction`, `refactor`, `technical debt`

**Knowledge:** DOCUMENTATION.md, SYSTEM_DESIGN.md

**Focus:** Shipping velocity, appropriate abstractions, sustainable decisions.

**Key questions:**
- Is this the right level of abstraction?
- Are we over-engineering or under-engineering?
- What's the maintenance burden?
- Is this reversible?

---

### product-engineer

**Triggers:** `product`, `feature`, `user`, `ux`, `requirements`, `metrics`, `analytics`

**Knowledge:** API_DESIGN.md, ERROR_HANDLING.md

**Focus:** User value, feature completeness, measurable outcomes.

**Key questions:**
- What problem does this solve?
- How do we know it's working?
- What's the user journey?
- What's the fallback experience?

---

### accessibility-engineer

**Triggers:** `accessibility`, `a11y`, `wcag`, `aria`, `screen reader`, `keyboard`, `frontend`, `ui`

**Always runs for:** `frontend` domain

**Knowledge:** TESTING.md

**Focus:** Keyboard navigation, screen readers, color contrast.

**Key questions:**
- Can I use this with keyboard only?
- What does a screen reader announce?
- Is there sufficient color contrast?
- Are form inputs properly labeled?

---

### mobile-engineer

**Triggers:** `mobile`, `ios`, `android`, `react native`, `flutter`, `app`, `bundle size`, `offline`

**Knowledge:** ERROR_HANDLING.md, TESTING.md

**Focus:** Offline capability, bundle size, platform constraints.

**Key questions:**
- Does this work offline?
- What's the impact on bundle size?
- How does this affect battery life?
- What happens on slow networks?

---

### uiux-engineer

**Triggers:** `ui`, `ux`, `design`, `component`, `css`, `styling`, `animation`, `design system`

**Knowledge:** TYPE_SAFETY.md

**Focus:** Design consistency, interaction patterns, user feedback.

**Key questions:**
- Is this using the design system?
- Is the feedback immediate and clear?
- Are animations purposeful?
- Does this handle all visual states?

---

### fde-engineer

**Triggers:** `integration`, `customer`, `configuration`, `sdk`, `api client`, `onboarding`, `enterprise`

**Knowledge:** API_DESIGN.md, DOCUMENTATION.md, ERROR_HANDLING.md

**Focus:** Customer deployability, configurability, integration ease.

**Key questions:**
- Can the customer configure this themselves?
- What's the integration complexity?
- How do we troubleshoot customer issues?
- What documentation does this need?

---

### customer-success

**Triggers:** `support`, `documentation`, `error message`, `user facing`, `help`, `troubleshoot`

**Knowledge:** DOCUMENTATION.md, ERROR_HANDLING.md

**Focus:** Supportability, clear communication, reducing tickets.

**Key questions:**
- What's the support ticket going to say?
- Can customers self-serve this issue?
- Is the error message actionable?
- How do we diagnose this remotely?

---

### gas-optimizer

**Triggers:** `gas`, `optimization`, `solidity`, `evm`, `storage`, `calldata`, `assembly`

**Always runs for:** `smart_contract` domain

**Knowledge:** SMART_CONTRACT.md

**Focus:** Storage optimization, calldata vs memory, loop efficiency.

**Key questions:**
- What's the gas cost of this function?
- Can storage reads/writes be reduced?
- Is calldata used instead of memory?
- Can this use unchecked math safely?

---

### protocol-architect

**Triggers:** `protocol`, `defi`, `tokenomics`, `governance`, `upgradeable`, `proxy`, `diamond`

**Always runs for:** `smart_contract` domain

**Knowledge:** SMART_CONTRACT.md, SECURITY.md

**Focus:** Economic security, upgrade paths, systemic risks.

**Key questions:**
- What's the economic attack surface?
- How does this compose with other protocols?
- What's the upgrade/governance path?
- Are there admin keys? What's the trust model?

---

### mev-researcher

**Triggers:** `mev`, `frontrun`, `sandwich`, `flashloan`, `arbitrage`, `mempool`, `searcher`

**Always runs for:** `smart_contract` domain

**Knowledge:** SMART_CONTRACT.md, SECURITY.md

**Focus:** Front-running, sandwich attacks, flash loan vulnerabilities.

**Key questions:**
- Can this transaction be front-run profitably?
- Is there sandwich attack potential?
- Can flash loans manipulate this?
- Is there slippage/deadline protection?

---

### formal-verification

**Triggers:** `formal verification`, `invariant`, `specification`, `proof`, `certora`, `halmos`, `symbolic`

**Knowledge:** SMART_CONTRACT.md, TESTING.md

**Focus:** Invariants, specifications, edge case coverage.

**Key questions:**
- What are the critical invariants?
- Can this property be formally specified?
- What assumptions does correctness depend on?
- Are there edge cases testing won't find?

---

### incident-responder

**Triggers:** `incident`, `outage`, `postmortem`, `recovery`, `rollback`, `hotfix`, `emergency`

**Knowledge:** OBSERVABILITY.md, SECURITY.md

**Focus:** Recoverability, debuggability, blast radius containment.

**Key questions:**
- If this fails at 3am, can we recover?
- What's the blast radius?
- Can we rollback quickly?
- Is there a kill switch?

---

### code-hygiene

**Triggers:** `dead code`, `cleanup`, `refactor`, `simplify`, `hygiene`

**Knowledge:** DOCUMENTATION.md

**Focus:** Code cleanliness, dead code removal, simplification.

**Key questions:**
- Is there unreachable or dead code?
- Can this be simplified?
- Are there unused imports or variables?
- Is the code well-organized?

---

### spec-reviewer

**Triggers:** `prd`, `spec`, `tdd`, `design`, `requirements`, `rfc`, `adr`

**Type:** Pre-write skill

**Knowledge:** SECURITY.md, DOCUMENTATION.md

**Focus:** Specification completeness, security requirements, failure modes.

**Key questions:**
- Are authentication/authorization requirements specified?
- Are failure modes documented?
- Are edge cases addressed?
- Is the scope clear and bounded?

---

## Skill Frontmatter

Each skill has YAML frontmatter:

```yaml
---
version: "1.0"
triggers: [keyword1, keyword2, ...]
always_run: true  # Optional: always include this skill
always_run_for_domains: [smart_contract]  # Optional: include for these domains
knowledge: [FILE1.md, FILE2.md]  # Optional: linked knowledge files
---
```

**Triggers** - Keywords that cause Claude to load this skill when they appear in context.

**always_run** - Skill is always loaded (e.g., security-engineer).

**always_run_for_domains** - Skill loads when domain matches (e.g., gas-optimizer for smart_contract).

**knowledge** - Engineering principles loaded when skill is active.

---

## Quick Reference Table

| Skill | Primary Focus | Domain |
|-------|--------------|--------|
| security-engineer | Vulnerabilities, auth, secrets | All |
| web3-engineer | Smart contract security | Smart Contract |
| backend-engineer | APIs, databases, reliability | Backend |
| performance-engineer | Latency, throughput, caching | Backend |
| devops-engineer | Deployment, observability | Infrastructure |
| data-engineer | Schemas, migrations, integrity | Backend |
| tech-lead | Architecture, abstractions | All |
| product-engineer | Features, user experience | All |
| accessibility-engineer | a11y, WCAG compliance | Frontend |
| mobile-engineer | Offline, bundle size | Mobile |
| uiux-engineer | Design system, states | Frontend |
| fde-engineer | Integration, configuration | All |
| customer-success | Error messages, support | All |
| gas-optimizer | Gas costs, storage | Smart Contract |
| protocol-architect | DeFi, governance | Smart Contract |
| mev-researcher | Front-running, flash loans | Smart Contract |
| formal-verification | Invariants, proofs | Smart Contract |
| incident-responder | Recovery, rollback | All |
| code-hygiene | Dead code, cleanup | All |
| spec-reviewer | PRD/TDD/RFC review | Pre-Write |
