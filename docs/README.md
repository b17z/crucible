# Crucible Documentation

Documentation index with links to core codebase components.

## Quick Links

| Doc | Purpose |
|-----|---------|
| [QUICKSTART.md](QUICKSTART.md) | 5-minute setup guide |
| [FEATURES.md](FEATURES.md) | Complete feature reference |
| [ARCHITECTURE.md](ARCHITECTURE.md) | How MCP, tools, skills, and knowledge fit together |
| [CUSTOMIZATION.md](CUSTOMIZATION.md) | Override skills, knowledge, and assertions |
| [SKILLS.md](SKILLS.md) | All 20 personas with triggers and focus |
| [KNOWLEDGE.md](KNOWLEDGE.md) | All 14 knowledge files |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Adding tools, skills, and knowledge |

## Feature → Code Mapping

### Core Features

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **MCP Server** | `crucible-mcp` | [`server.py`](../src/crucible/server.py) |
| **CLI** | `crucible` | [`cli.py`](../src/crucible/cli.py) |
| **Domain Detection** | `review()` | [`domain/detection.py`](../src/crucible/domain/detection.py) |
| **Tool Delegation** | `delegate_*()` | [`tools/delegation.py`](../src/crucible/tools/delegation.py) |

### Enforcement

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **Pattern Assertions** | `run_pattern_assertions()` | [`enforcement/patterns.py`](../src/crucible/enforcement/patterns.py) |
| **LLM Assertions** | `run_compliance_assertions()` | [`enforcement/compliance.py`](../src/crucible/enforcement/compliance.py) |
| **Assertion Loading** | `load_assertions()` | [`enforcement/assertions.py`](../src/crucible/enforcement/assertions.py) |
| **Bundled Assertions** | 30 rules | [`enforcement/bundled/`](../src/crucible/enforcement/bundled/) |

### Hooks

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **Pre-commit Hook** | `crucible hooks install` | [`hooks/precommit.py`](../src/crucible/hooks/precommit.py) |
| **Claude Code PostToolUse** | `crucible hooks claudecode hook` | [`hooks/claudecode.py`](../src/crucible/hooks/claudecode.py) |
| **Claude Code SessionStart** | `crucible hooks claudecode session` | [`hooks/claudecode.py`](../src/crucible/hooks/claudecode.py) |
| **Session Context** | Auto-inject | [`history.py`](../src/crucible/history.py) |

### Skills & Knowledge

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **Skill Loading** | `load_skill()` | [`skills/loader.py`](../src/crucible/skills/loader.py) |
| **Bundled Skills** | 20 personas | [`skills/*/SKILL.md`](../src/crucible/skills/) |
| **Knowledge Loading** | `load_knowledge()` | [`knowledge/loader.py`](../src/crucible/knowledge/loader.py) |
| **Bundled Knowledge** | 14 files | [`knowledge/principles/`](../src/crucible/knowledge/principles/) |

### Pre-Write Review

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **Pre-write Review** | `prewrite_review()` | [`prewrite/review.py`](../src/crucible/prewrite/review.py) |
| **Template Loading** | `load_template()` | [`prewrite/loader.py`](../src/crucible/prewrite/loader.py) |
| **Bundled Templates** | 5 templates | [`templates/prewrite/`](../src/crucible/templates/prewrite/) |

### Git Integration

| Feature | Entry Point | Key Files |
|---------|-------------|-----------|
| **Staged Changes** | `review(mode='staged')` | [`tools/git.py`](../src/crucible/tools/git.py) |
| **Branch Diff** | `review(mode='branch')` | [`tools/git.py`](../src/crucible/tools/git.py) |
| **Ignore Patterns** | `.crucibleignore` | [`ignore.py`](../src/crucible/ignore.py) |

## Directory Structure

```
src/crucible/
├── server.py              # MCP server - tool definitions
├── cli.py                 # CLI commands
├── models.py              # Domain, Severity, ToolFinding
├── errors.py              # Result types (Ok/Err)
├── ignore.py              # .crucibleignore handling
├── history.py             # Session continuity
│
├── domain/
│   └── detection.py       # Classify code by extension/content
│
├── tools/
│   ├── delegation.py      # Shell out to analysis tools
│   └── git.py             # Git operations
│
├── hooks/
│   ├── precommit.py       # Git pre-commit hook
│   └── claudecode.py      # Claude Code hooks
│
├── enforcement/
│   ├── assertions.py      # Load/validate YAML assertions
│   ├── patterns.py        # Pattern matching
│   ├── compliance.py      # LLM assertions
│   ├── models.py          # Assertion, Finding models
│   └── bundled/           # 30 bundled assertions
│
├── skills/
│   ├── loader.py          # Skill loading with cascade
│   └── <skill>/SKILL.md   # 20 bundled personas
│
├── knowledge/
│   ├── loader.py          # Knowledge loading
│   └── principles/        # 14 bundled files
│
├── prewrite/
│   ├── loader.py          # Template loading
│   ├── review.py          # Pre-write review logic
│   └── models.py          # PrewriteMetadata
│
└── templates/prewrite/    # 5 bundled templates
```

## Cascade Resolution

All customizable content follows the same resolution order:

```
1. .crucible/              # Project (highest priority)
2. ~/.claude/crucible/     # User
3. <package>/              # Bundled (lowest)
```

First found wins. See [CUSTOMIZATION.md](CUSTOMIZATION.md) for details.

## Historical / Planning Docs

| Doc | Purpose |
|-----|---------|
| [PLAN_1.0.md](PLAN_1.0.md) | Original 1.0 release plan (historical) |
| [RFC_ENFORCEMENT.md](RFC_ENFORCEMENT.md) | Enforcement design decisions |
| [FUTURE_ENHANCEMENTS.md](FUTURE_ENHANCEMENTS.md) | Ideas for future development |
| [SAGE_INTEGRATION.md](SAGE_INTEGRATION.md) | Sage MCP integration notes |
| [RESEARCH_CONTEXT_ARCHITECTURE.md](RESEARCH_CONTEXT_ARCHITECTURE.md) | Research context design |

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `test_server.py` | MCP tools |
| `test_detection.py` | Domain detection |
| `test_tools.py` | Tool delegation |
| `test_enforcement.py` | Assertions |
| `test_precommit.py` | Pre-commit hooks |
| `test_hooks_cli.py` | Hook CLI |
| `test_skills_loader.py` | Skill loading |
| `test_knowledge.py` | Knowledge loading |
| `test_prewrite.py` | Pre-write review |
| `test_activation.py` | Session context |
| `test_cli.py` | CLI commands |
| `test_integration.py` | End-to-end |

**Total: 669 tests**
