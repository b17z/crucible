# Contributing to Crucible

For contributors: directory structure, adding tools, and design decisions.

## Quick Start

```bash
# Clone and install
git clone https://github.com/b17z/crucible.git
cd crucible
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ --fix
```

---

## Directory Structure

```
src/crucible/
├── server.py              # MCP server - tool definitions and handlers
├── cli.py                 # CLI commands (skills/knowledge management)
├── models.py              # Data models (Domain, Severity, ToolFinding)
├── errors.py              # Result types (Ok/Err pattern)
│
├── domain/
│   └── detection.py       # Classify code by extension/content
│
├── tools/
│   └── delegation.py      # Shell out to analysis tools
│
├── knowledge/
│   ├── loader.py          # Load principles with cascade resolution
│   └── principles/        # 12 bundled knowledge files
│       ├── SECURITY.md
│       ├── TESTING.md
│       └── ...
│
└── skills/                # 18 bundled persona skills
    ├── security-engineer/SKILL.md
    ├── web3-engineer/SKILL.md
    └── ...

tests/
├── test_server.py         # MCP tool tests
├── test_detection.py      # Domain detection tests
├── test_tools.py          # Tool delegation tests
├── test_knowledge.py      # Knowledge loader tests
├── test_skills.py         # Skill validation tests
├── test_cli.py            # CLI command tests
└── test_integration.py    # End-to-end tests with fixtures

tests/fixtures/
├── vulnerable_python.py   # Python security vulnerabilities
├── vulnerable_sol/        # Solidity vulnerabilities
└── ...

docs/
├── ARCHITECTURE.md        # How the pieces fit together
├── CUSTOMIZATION.md       # Skills + knowledge cascade
├── SKILLS.md              # All 18 personas
├── KNOWLEDGE.md           # All 12 knowledge files
└── CONTRIBUTING.md        # This document
```

---

## Adding New Analysis Tools

### 1. Add Delegation Function

In `tools/delegation.py`:

```python
def delegate_mytool(path: str) -> Result[list[ToolFinding], str]:
    """Run mytool analysis."""
    if not _check_tool("mytool"):
        return err("mytool not installed. Install: pip install mytool")

    try:
        result = subprocess.run(
            ["mytool", "--json", path],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return err("mytool timed out")

    # Parse output and map to ToolFinding
    findings = []
    for item in json.loads(result.stdout):
        findings.append(ToolFinding(
            tool="mytool",
            rule=item["rule_id"],
            severity=_map_mytool_severity(item["severity"]),
            message=item["message"],
            location=f"{item['file']}:{item['line']}",
            suggestion=item.get("fix"),
        ))

    return ok(findings)
```

### 2. Add MCP Tool Handler

In `server.py`:

```python
# Add to list_tools()
Tool(
    name="delegate_mytool",
    description="Run mytool analysis",
    inputSchema={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File or directory to scan"},
        },
        "required": ["path"],
    },
),

# Add handler function
def _handle_delegate_mytool(arguments: dict[str, Any]) -> list[TextContent]:
    path = arguments.get("path", "")
    result = delegate_mytool(path)
    if result.is_ok:
        return [TextContent(type="text", text=_format_findings(result.value))]
    return [TextContent(type="text", text=f"Error: {result.error}")]

# Add to handlers dict in call_tool()
"delegate_mytool": _handle_delegate_mytool,
```

### 3. Update Domain → Tools Mapping

In `_handle_quick_review()`:

```python
# Add to appropriate domain
if domain == Domain.BACKEND and "python" in domain_tags:
    default_tools = ["ruff", "bandit", "semgrep", "mytool"]  # Add here
```

### 4. Add Tests

In `tests/test_tools.py`:

```python
def test_mytool_severity_mapping():
    assert _map_mytool_severity("error") == Severity.HIGH
    assert _map_mytool_severity("warning") == Severity.MEDIUM
```

In `tests/test_integration.py`:

```python
def test_mytool_detects_issue():
    result = delegate_mytool("tests/fixtures/vulnerable_file.py")
    assert result.is_ok
    assert any("ISSUE_CODE" in f.rule for f in result.value)
```

---

## Adding New Skills (Personas)

### 1. Create Skill Directory

```bash
mkdir -p src/crucible/skills/my-persona
```

### 2. Create SKILL.md

```yaml
# src/crucible/skills/my-persona/SKILL.md
---
version: "1.0"
triggers: [keyword1, keyword2, keyword3]
knowledge: [RELEVANT.md]
---

# My Persona

You are reviewing code from [perspective]. Your focus is on [focus area].

## Key Questions

Ask yourself these questions about the code:

- Question 1?
- Question 2?
- Question 3?

## Red Flags

Watch for these patterns:

- Pattern 1
- Pattern 2
- Pattern 3

## Before Approving

Verify these criteria:

- [ ] Checklist item 1
- [ ] Checklist item 2
- [ ] Checklist item 3

## Output Format

Structure your review as:

### Section 1
Issues in category 1.

### Section 2
Issues in category 2.

### Approval Status
- APPROVE: Ready
- REQUEST CHANGES: Issues must be addressed
- COMMENT: Suggestions only
```

### 3. Add Tests

In `tests/test_skills.py`, the existing tests will automatically validate:
- SKILL.md exists
- Has valid YAML frontmatter
- Has version
- Has triggers
- Has title (# heading)

---

## Adding New Knowledge

### 1. Create Knowledge File

```bash
# Create in bundled location
touch src/crucible/knowledge/principles/MY_TOPIC.md
```

### 2. Write Content

```markdown
# My Topic Principles

Brief description of what this covers.

---

## Section 1

Content...

---

## Section 2

Content...

---

*Template. Customize for your needs.*
```

### 3. Link from Skills

Update relevant skill frontmatter:

```yaml
---
knowledge: [MY_TOPIC.md, OTHER.md]
---
```

### 4. Update Topic Mapping (if needed)

In `knowledge/loader.py`:

```python
topic_files = {
    "my_topic": ["MY_TOPIC.md"],  # Add new topic
    # ...
}
```

### 5. Add Tests

In `tests/test_knowledge.py`:

```python
def test_my_topic_file_exists(self) -> None:
    path = KNOWLEDGE_BUNDLED / "MY_TOPIC.md"
    assert path.exists()
    content = path.read_text()
    assert "expected content" in content.lower()
```

---

## Test Organization

| Test File | What It Tests |
|-----------|---------------|
| `test_server.py` | MCP tool handlers, domain detection |
| `test_detection.py` | Extension and content-based detection |
| `test_tools.py` | Tool delegation, severity mapping |
| `test_knowledge.py` | Knowledge loading, cascade resolution |
| `test_skills.py` | Skill validation (frontmatter, structure) |
| `test_cli.py` | CLI commands (install, list, init, show) |
| `test_integration.py` | End-to-end with vulnerable fixtures |

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/test_skills.py -v

# Specific test
pytest tests/test_skills.py::TestSkillMetadata::test_has_version -v

# With coverage
pytest --cov=crucible
```

---

## Design Decisions

### Why MCP instead of direct integration?

MCP (Model Context Protocol) is Claude's standard for tool integration. It works with Claude Code, Claude Desktop, and agents. Crucible provides data (findings, domains), Claude provides reasoning.

### Why shell out to tools instead of Python libraries?

- Tools have their own release cycles
- Users can update tools independently
- Consistent output format across versions
- Easier to add new tools

### Why cascade resolution for skills/knowledge?

- Project needs override defaults (team conventions)
- User preferences without forking (personal style)
- Bundled templates as starting point
- No configuration files to maintain

### Why Result types instead of exceptions?

- Explicit error handling
- Caller must acknowledge errors
- Type-safe error information
- No hidden control flow

### Why frozen dataclasses for models?

- Immutable by default
- Safe to use as dict keys
- Clear data boundaries
- Prevents accidental mutation

---

## Code Style

- **Formatting:** ruff (auto-formatted)
- **Type hints:** Required for function signatures
- **Docstrings:** Required for public functions
- **Error handling:** Result types, not exceptions
- **Naming:** snake_case for functions/variables, PascalCase for classes

---

## Commit Messages

Format: `(type): description`

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code restructure
- `test` - Tests
- `chore` - Build, deps

Examples:
```
(feat): add bandit tool delegation
(fix): handle empty semgrep output
(docs): add gas-optimizer skill
(test): add reentrancy detection test
```

---

## Before Submitting

1. Tests pass: `pytest`
2. Linting clean: `ruff check src/`
3. New features have tests
4. Documentation updated if needed
