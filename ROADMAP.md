# crucible Roadmap

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
- [x] Convert core personas to skills:
  - [x] backend-engineer
  - [x] devops-engineer
  - [x] performance-engineer
  - [x] accessibility-engineer
  - [x] data-engineer
  - [x] product-engineer
  - [x] tech-lead
- [x] Add remaining personas:
  - [x] mobile-engineer
  - [x] uiux-engineer
  - [x] fde-engineer
  - [x] customer-success
  - [x] gas-optimizer (web3)
  - [x] protocol-architect (web3)
  - [x] mev-researcher (web3)
  - [x] formal-verification
  - [x] incident-responder

**Total: 18 skills**

### Phase 4: Skill Customization
- [x] Project-level skill overrides (`.crucible/skills/`)
- [x] Skill resolution cascade (project → user → bundled)
- [x] CLI: `crucible skills init <skill>` - copy skill for customization
- [x] CLI: `crucible skills show <skill>` - show resolution
- [x] Skill version metadata
- [x] Comprehensive test suite (257 tests, 69% coverage)

## In Progress

### Phase 5: Polish
- [ ] Skill trigger refinement (test which domains auto-load which skills)
- [ ] Increase test coverage to 80%+

## Future

### Multi-Tool Polish
- [ ] Better semgrep configs per domain
- [ ] ESLint delegation for TypeScript
- [ ] Unified finding deduplication
- [ ] Caching for repeated scans

### MCP Composition
- [ ] Use slither-mcp instead of shell out (when stable)
- [ ] Use semgrep-mcp instead of shell out (when available)

### Knowledge Evolution
- [ ] Domain-specific principle files
- [ ] Principle citation in reviews

### Integration
- [ ] GitHub PR integration (review PR diffs)
- [ ] CI mode output format (SARIF, GitHub annotations)
- [ ] Integration with Sage (checkpoint review sessions)

## Design Decisions

### Tensions
Claude synthesizes tensions naturally when multiple skills are loaded. No explicit tension detection algorithm needed - skills provide conflicting guidance, Claude identifies trade-offs. See `docs/FUTURE_ENHANCEMENTS.md` for alternatives if needed.

### Personas → Skills
Personas moved from MCP to Claude skills. Benefits:
- Claude auto-loads based on domain triggers
- Skills can be customized per-project
- MCP stays stateless and simple
