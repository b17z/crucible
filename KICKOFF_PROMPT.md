# crucible: Claude Code Kickoff Prompt

Copy and paste this into Claude Code to start the project.

---

## The Prompt

```
I'm building crucible, an MCP server for code review orchestration.

Read SPEC.md for full details, but the core idea:

1. **Compose** existing analysis MCPs (slither, semgrep, eslint, ruff) — don't rebuild
2. **Apply** engineering principles as review context
3. **Route** to relevant senior engineer personas (Security, Gas, Protocol, etc.)
4. **Surface** tensions between personas ("Security wants X, Gas wants Y")
5. **Synthesize** actionable recommendations

## Phase 1 Goals (MVP)

Build the foundation:
- [ ] MCP server skeleton (Python, stdio transport)
- [ ] Domain detection from file extensions (.sol → smart_contract, .tsx → frontend)
- [ ] Single delegation: shell out to semgrep (we'll add MCP composition later)
- [ ] Load principles from markdown files in knowledge/
- [ ] Single persona: Security Engineer
- [ ] Basic synthesis (tool findings + persona review → markdown output)

## Constraints

- Python 3.11+, use `mcp` SDK
- Functional-first (dataclasses OK, no class hierarchies)
- Types everywhere (`mypy --strict`)
- Tests for each module
- No features not in spec

## Start With

1. Set up project structure per SPEC.md
2. Create pyproject.toml with dependencies
3. Implement domain detection (simplest first: file extension mapping)
4. Get a hello-world MCP server running
5. Add the `review` tool that returns static output
6. Then iterate

Don't do everything at once. Ship incrementally. Verify each step works before moving on.
```

---

## Alternative: Phased Prompts

If you prefer smaller chunks, use these in sequence:

### Prompt 1: Project Setup
```
Set up the crucible project structure:
- Create directory structure per SPEC.md
- Create pyproject.toml with: mcp, pyyaml, pytest, mypy, ruff
- Create empty __init__.py files
- Create a minimal CLAUDE.md (copy from the one I provided)
- Verify: `pip install -e .` works
```

### Prompt 2: MCP Skeleton
```
Create a minimal MCP server in src/crucible/server.py that:
- Uses stdio transport
- Has one tool: `ping` that returns "pong"
- Verify: test manually with MCP inspector or by running directly
```

### Prompt 3: Domain Detection
```
Implement domain detection in src/crucible/domain/detection.py:
- detect_domain(file_path: str) -> Domain
- Use file extension mapping first (SPEC.md has the heuristics)
- Add tests in tests/test_detection.py
- Verify: pytest tests/test_detection.py passes
```

### Prompt 4: Review Tool
```
Add the `review` tool to the MCP server:
- Takes code: str and optional domain: str
- Auto-detects domain if not provided
- For now, returns a static placeholder response
- Verify: tool shows up in MCP inspector
```

### Prompt 5: Semgrep Integration
```
Add semgrep delegation in src/crucible/tools/delegation.py:
- delegate_semgrep(path: str, config: str) -> list[ToolFinding]
- Shell out to semgrep CLI (assume installed)
- Parse JSON output into ToolFinding dataclass
- Add tests with fixture files
```

### Prompt 6: Principles Loader
```
Implement principles loading in src/crucible/knowledge/loader.py:
- Load markdown files from knowledge/ directory
- Parse into structured format (or just return raw text for now)
- Add ENGINEERING_PRINCIPLES.md to knowledge/
- Verify: loader.get_principles() returns content
```

### Prompt 7: Security Persona
```
Implement the Security Engineer persona in src/crucible/personas/engine.py:
- invoke_persona(persona: Persona, code: str, findings: list[ToolFinding]) -> PersonaReview
- Hardcode Security Engineer prompt for now
- Returns: verdict, concerns, approvals, questions
- Add tests
```

### Prompt 8: Synthesis
```
Implement synthesis in src/crucible/synthesis/synthesizer.py:
- synthesize(domain, tool_findings, persona_reviews) -> ReviewResult
- Combine everything into markdown output
- Wire it up in the review tool
- Full end-to-end test: code in → review out
```

---

## After MVP

Once Phase 1 works:
- Add slither-mcp delegation (actual MCP composition, not shell)
- Add more personas
- Implement tension detection
- Structure principles as YAML

But don't plan too far ahead. Ship the MVP first.
