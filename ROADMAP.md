# crucible Roadmap

## Done (Phase 1 MVP)

- [x] MCP server skeleton (stdio transport)
- [x] Domain detection (extension + content markers)
- [x] Tool delegation: semgrep, ruff, slither (shell out)
- [x] Persona routing by domain (21 personas defined)
- [x] Knowledge loader (principles from markdown)
- [x] Basic `review` and `quick_review` tools
- [x] Result types (errors as values)
- [x] Tests for domain detection

## Phase 2: Multi-Tool Polish

- [ ] Better semgrep configs per domain (p/python, p/javascript, p/smart-contracts)
- [ ] ESLint delegation for TypeScript
- [ ] Unified finding deduplication (same issue from multiple tools)
- [ ] Severity normalization across tools
- [ ] Caching for repeated scans

## Phase 3: Persona Engine

- [ ] Persona prompt templates (structured, not just markdown extraction)
- [ ] Multi-persona review (invoke N personas, not just first)
- [ ] Tension detection algorithm (compare persona outputs)
- [ ] Synthesis: combine findings + personas + tensions into recommendation

## Phase 4: MCP Composition

- [ ] Use slither-mcp instead of shell out (when stable)
- [ ] Use semgrep-mcp instead of shell out (when available)
- [ ] Tool capability discovery (what's installed?)

## Phase 5: Knowledge Evolution

- [ ] Principles as structured YAML (not just markdown)
- [ ] Domain-specific principle files (SMART_CONTRACT_SECURITY.md, etc.)
- [ ] Checklist generation from persona approvals
- [ ] Principle citation in reviews ("violates: Defense in Depth")

## Ideas (Unscheduled)

- [ ] GitHub PR integration (review PR diffs directly)
- [ ] CI mode output format (SARIF, GitHub annotations)
- [ ] Custom persona injection (user-defined personas)
- [ ] Learning from past reviews (what got approved/rejected)
- [ ] Integration with Sage (checkpoint review sessions)
