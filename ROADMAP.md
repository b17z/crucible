# Crucible Roadmap

## Vision

**Crucible becomes the enforcement layer for the entire software development lifecycle** - from intent capture (pre-write) through production learning (post-merge) - with the persona framework as the differentiating core.

The goal: **"Load your engineering brain into code review."**

For teams: **"Load your team's 10 years of engineering decisions into every review."**

---

## Done

### Phase 1: MVP
- [x] MCP server skeleton (stdio transport)
- [x] Domain detection (extension + content markers)
- [x] Tool delegation: semgrep, ruff, slither
- [x] Knowledge loader (principles from markdown)
- [x] Result types (errors as values)
- [x] Tests for domain detection

### Phase 2: Architecture Refactor
- [x] Simplify MCP tools (remove persona logic from MCP)
- [x] Internal domain detection (returns metadata, not exposed as tool)
- [x] Unified `review()` tool with domain metadata + severity summary
- [x] CLI: `crucible skills install/list`
- [x] Initial skills: security-engineer, web3-engineer
- [x] Remove dead code (Persona enum, PERSONA_ROUTING, persona engine)
- [x] Expose delegate_bandit as MCP tool

**New architecture:** MCP = data, Skills = perspective, Claude = orchestrator

### Phase 3: Skills Expansion
- [x] 19 bundled personas covering engineering roles
- [x] Skill trigger matching (domain + tags intersection)
- [x] Knowledge linking (skills reference knowledge files)
- [x] Cascade resolution (project → user → bundled)

### Phase 4: Enforcement
- [x] 30 bundled assertions (security, error handling, smart contracts)
- [x] Pattern assertions (fast regex matching)
- [x] LLM assertions (semantic compliance checking)
- [x] Token budget management
- [x] Inline suppression system (`// crucible-ignore`)
- [x] Pre-commit hooks (`crucible hooks install`)
- [x] Claude Code hooks (`crucible hooks claudecode init`)

### Phase 5: Polish
- [x] CLI commands for assertions, skills, knowledge
- [x] `.crucibleignore` for file exclusion
- [x] Git-aware review modes (staged, unstaged, branch, commits)
- [x] 660+ tests

### Phase 6: Activation Energy (Partial)
- [x] SessionStart hook for context injection
- [x] Auto-inject enforcement summary at session start
- [x] `.crucible/system/` folder pattern for team context
- [x] Finding history in `.crucible/history/`
- [x] `crucible system init/show` commands

### Phase 7: Pre-Write Review
- [x] Pre-write skill type (`spec-reviewer`)
- [x] `prewrite_review(path)` MCP tool
- [x] `prewrite_list_templates()` MCP tool
- [x] `crucible prewrite` CLI commands
- [x] 5 bundled templates (PRD, TDD, RFC, ADR, Security Review)
- [x] Pre-write assertions (`scope: prewrite`)
- [x] Cascade resolution for templates

---

## The Full Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CRUCIBLE ENFORCEMENT STACK                       │
├──────────────┬──────────────────────────────────────────────────────────┤
│  PRE-WRITE   │ Spec/PRD/TDD review before code exists                   │
│              │ → Catch drift at the source                              │
├──────────────┼──────────────────────────────────────────────────────────┤
│  WHILE-WRITE │ Real-time enforcement in IDE                             │
│              │ → Flag violations as you type                            │
├──────────────┼──────────────────────────────────────────────────────────┤
│  PRE-COMMIT  │ Local hooks, staged file review               ✓ TODAY   │
│              │ → Block bad code before it leaves your machine           │
├──────────────┼──────────────────────────────────────────────────────────┤
│  PR REVIEW   │ Automated + human review                      ✓ TODAY   │
│              │ → Persona-based analysis with enforcement                │
├──────────────┼──────────────────────────────────────────────────────────┤
│  MERGE GATE  │ CI/CD blocking                                ✓ TODAY   │
│              │ → Actually blocks, unlike most AI tools                  │
├──────────────┼──────────────────────────────────────────────────────────┤
│  POST-MERGE  │ Production learning loop                                 │
│              │ → Learn from what works, what breaks                     │
└──────────────┴──────────────────────────────────────────────────────────┘
```

---

## Phase 6: Activation Energy (Remaining)

**Done:** Session context injection, system folder pattern, finding history.

### 6.3 Proactive Skill Activation
- [ ] File-type triggers in Claude Code hooks (PreToolUse on Read)
- [ ] Background skill matching on file open
- [ ] Lightweight context injection without full review

### 6.4 Sage Integration
- [ ] Checkpoint review sessions
- [ ] Cross-session context via Sage knowledge

---

## Phase 8: IDE Integration

**Problem:** Enforcement only happens at commit/PR time. By then, you've written the code.

### 8.1 VS Code Extension
- [ ] Build for VS Code → works in Cursor/Windsurf via Open VSX
- [ ] Inline violation highlighting
- [ ] Quick-fix suggestions for pattern violations
- [ ] Skill context in hover tooltips
- [ ] Pre-commit preview ("what would Crucible catch?")

### 8.2 Extension Features
```
crucible-vscode/
├── src/
│   ├── diagnostics.ts        # Inline violation highlighting
│   ├── quickfix.ts           # One-click fixes for patterns
│   ├── hover.ts              # Skill context on hover
│   └── preview.ts            # Pre-commit preview
```

**IDE Landscape 2026:**
| Editor | Strategy |
|--------|----------|
| VS Code | Primary target (75% market share) |
| Cursor | Works via Open VSX (~95% compat) |
| Windsurf | Works via Open VSX |
| Warp | Already works via MCP |
| JetBrains | Future (own ecosystem) |

---

## Phase 9: Post-Merge Learning

**Problem:** Enforcement is static. No feedback loop from production.

### 9.1 Finding History
- [ ] Track all findings in `.crucible/history/findings.jsonl`
- [ ] Track suppressions with reasons
- [ ] Track resolutions (how findings were fixed)

### 9.2 Suppression Analytics
- [ ] `crucible analytics suppressions` - what's being ignored
- [ ] Identify noisy assertions (high suppression rate)
- [ ] Suggest assertion tuning based on patterns

### 9.3 Incident Correlation
- [ ] Map production issues to code patterns
- [ ] Identify assertion gaps ("this incident would have been caught by...")
- [ ] Feed incidents back into enforcement

### 9.4 Effectiveness Dashboard
- [ ] `crucible analytics effectiveness` - which assertions catch real bugs
- [ ] False positive tracking
- [ ] Auto-tuning suggestions

```bash
crucible analytics effectiveness

# Assertion                          | Catches | FP Rate | Effectiveness
# -----------------------------------|---------|---------|---------------
# no-eval                            | 47      | 4%      | 96%
# hardcoded-secrets                  | 8       | 0%      | 100%
# missing-error-handling             | 123     | 28%     | 72%
```

---

## Phase 10: New Personas

**Current:** 20 bundled personas (security-engineer, web3-engineer, backend-engineer, performance-engineer, devops-engineer, data-engineer, tech-lead, product-engineer, accessibility-engineer, mobile-engineer, uiux-engineer, fde-engineer, customer-success, gas-optimizer, protocol-architect, mev-researcher, formal-verification, incident-responder, code-hygiene, spec-reviewer)

### Tier 1 - Critical Gaps
- [ ] **QA/Testing Engineer** - testability, coverage gaps, test maintainability
- [ ] **Compliance Officer** - GDPR, HIPAA, SOC2, regulatory requirements
- [ ] **Reliability/Chaos Engineer** - failure modes, resilience patterns, graceful degradation

### Tier 2 - Domain-Specific
- [ ] **Technical Writer** - API docs, ADRs, README quality
- [ ] **FinOps/Cost Engineer** - cloud spend, infrastructure costs
- [ ] **ML Ops Engineer** - model deployment, bias, drift detection

### Tier 3 - Specialized
- [ ] **Database Architect** - index strategy, sharding, query optimization
- [ ] **API Designer** - REST/GraphQL principles, versioning
- [ ] **Payments Compliance** - AML/KYC, sanctions, fintech regulations

### Tier 4 - Emerging
- [ ] **Kubernetes Operator** - CRDs, operators, cluster security
- [ ] **Localization Engineer** - i18n for global teams
- [ ] **GraphQL Specialist** - N+1 prevention, federation

---

## Phase 11: Cross-Service Awareness

**Problem:** Crucible reviews single repos. Modern systems span services.

### 11.1 Multi-Repo Context
- [ ] `.crucible/services.yaml` - declare service dependencies
- [ ] Cross-repo context loading
- [ ] Service boundary awareness

### 11.2 Breaking Change Detection
- [ ] "This endpoint is consumed by 3 services"
- [ ] "Removing this field will break api-gateway"
- [ ] Contract testing integration (Pact, etc.)

---

## Future

### Multi-Tool Polish
- [ ] Better semgrep configs per domain
- [ ] ESLint delegation for TypeScript
- [ ] Unified finding deduplication
- [ ] Caching for repeated scans

### MCP Composition
- [ ] Use slither-mcp instead of shell out (when stable)
- [ ] Use semgrep-mcp instead of shell out (when available)

### Integration
- [ ] GitHub PR integration (review PR diffs, post comments)
- [ ] CI mode output format (SARIF, GitHub annotations)
- [ ] Integration with Sage (checkpoint review sessions)

---

## Design Principles

### 1. Plug and Play
Crucible provides sensible defaults. Teams bring their own:
- Pre-write templates
- Custom personas
- Team-specific assertions
- Compliance requirements

The cascade model enables this without forking.

### 2. Invisible When Working
The best enforcement is enforcement you don't think about:
- Context auto-injected at session start
- Skills activate based on what you're editing
- Violations surface in real-time
- Clean commits because issues caught while writing

### 3. Actually Blocks
Unlike most AI tools that only comment:
- Pre-commit hooks block
- CI gates block
- Claude Code hooks block

Enforcement, not suggestion.

### 4. Teaches, Not Just Catches
Assertions alone don't teach. The knowledge system creates learning:
- Catch the pattern → explain why it's bad → show how to fix

### 5. Learns Over Time
Static enforcement gets stale. The learning loop improves:
- Track what gets caught
- Learn from suppressions
- Correlate with production issues
- Auto-tune based on effectiveness

---

## Milestone Summary

| Phase | Focus | Status |
|-------|-------|--------|
| **1-5** | MVP, Architecture, Skills, Enforcement, Polish | Done |
| **6** | Activation Energy | Partial (session context done, proactive activation pending) |
| **7** | Pre-Write | Done |
| **8** | IDE | Planned |
| **9** | Post-Merge | Planned |
| **10** | Personas | 20 done, more planned |
| **11** | Cross-Service | Planned |

---

## Appendix: Design Decisions

### Tensions
Claude synthesizes tensions naturally when multiple skills are loaded. No explicit tension detection algorithm needed - skills provide conflicting guidance, Claude identifies trade-offs.

### Personas → Skills
Personas moved from MCP to Claude skills. Benefits:
- Claude auto-loads based on domain triggers
- Skills can be customized per-project
- MCP stays stateless and simple

### Pre-Write Philosophy
The insight from Anthropic's practices: "Each handoff introduces drift."

Pre-write templates are **guides, not gates**. They help teams think through decisions before committing to code, while staying lightweight enough to not slow down prototype-first workflows.

Teams bring their own templates. Crucible provides starting points. The cascade model means org-wide templates can be shared while individual teams customize.
