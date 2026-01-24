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
- [x] Simplify MCP to 6 tools (remove persona logic from MCP)
- [x] Internal domain detection (returns metadata, not exposed as tool)
- [x] `quick_review` returns `domains_detected` + `severity_summary`
- [x] CLI: `crucible skills install/list`
- [x] Initial skills: security-engineer, web3-engineer
- [x] Remove dead code (Persona enum, PERSONA_ROUTING, persona engine)

**New architecture:** MCP = data, Skills = perspective, Claude = orchestrator

## In Progress

### Phase 3: Skills Expansion
- [ ] Convert remaining personas to skills (backend, devops, performance, etc.)
- [ ] Skill trigger refinement (test which domains auto-load which skills)
- [ ] Project-level skill overrides (`.claude/skills/crucible/`)

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
