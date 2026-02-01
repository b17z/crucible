# Quick Start Guide

Get Crucible running in 5 minutes.

---

## 1. Install

```bash
pip install crucible-mcp
```

## 2. Initialize Your Project

```bash
cd your-project
crucible init --with-claudemd
```

This creates:
- `.crucible/` directory for customization
- `CLAUDE.md` pointing to Crucible (~50 tokens)

## 3. Install Hooks

```bash
# Git pre-commit hook (runs on every commit)
crucible hooks install

# Claude Code hooks (reviews files Claude edits)
crucible hooks claudecode init
```

## 4. Add to Claude Code

Add to your `.mcp.json`:

```json
{
  "mcpServers": {
    "crucible": {
      "command": "crucible-mcp"
    }
  }
}
```

---

## What Happens Now

### On Every Commit

The pre-commit hook runs:
1. Secrets detection (blocks .env, keys, credentials)
2. Static analysis (semgrep, ruff, bandit, slither)
3. Pattern assertions (30 bundled rules)

```bash
$ git commit -m "Add feature"

Checking for secrets...
Running static analysis...
Running pattern assertions...

Checked 3 file(s), 12 assertion(s) - no issues found
```

If violations are found:

```bash
BLOCKED: Possible security issue

[ERROR] no-eval: eval() is dangerous - use ast.literal_eval()
  at src/parser.py:42:5
  matched: eval(

Pre-commit: FAILED
Fix issues or use --no-verify to skip.
```

### When Claude Edits Files

The Claude Code hook reviews every `Edit` and `Write`:

```
Claude: Writing src/auth.py...
Crucible: [Pattern assertion] no-shell-true triggered
Crucible: Exit 2 → Block + feedback to Claude

Claude sees:
"Crucible found 1 issue(s) in src/auth.py:
[ERROR] no-shell-true: shell=True enables shell injection
  at src/auth.py:15:1"

Claude: Fixing the issue...
```

---

## Customize

### Add Project-Specific Assertions

```bash
mkdir -p .crucible/assertions
```

Create `.crucible/assertions/my-rules.yaml`:

```yaml
version: "1.0"
name: my-rules
description: Project-specific rules
assertions:
  - id: no-print-statements
    type: pattern
    pattern: "\\bprint\\s*\\("
    message: "Use logging instead of print"
    severity: warning
    priority: medium
    languages: [python]
    applicability:
      exclude:
        - "**/test_*.py"
```

### Override Bundled Skills

```bash
crucible skills init security-engineer
# Edit .crucible/skills/security-engineer/SKILL.md
```

### Add Project Knowledge

```bash
crucible knowledge init SECURITY
# Edit .crucible/knowledge/SECURITY.md
```

---

## CLI Commands

```bash
# Review changes
crucible review                     # Staged changes
crucible review --mode branch       # Branch vs main
crucible review src/file.py --no-git # Specific file

# List what's available
crucible assertions list            # Assertion files
crucible skills list                # Review personas
crucible knowledge list             # Knowledge files

# Check tool installation
crucible check-tools                # Show what's installed
```

---

## Configuration

### Pre-commit: `.crucible/precommit.yaml`

```yaml
fail_on: high                       # critical, high, medium, low, info
run_assertions: true                # Pattern assertions (fast, free)
run_llm_assertions: false           # LLM assertions (slow, costs $)
llm_token_budget: 5000              # Token limit for LLM assertions
exclude:
  - "*.md"
  - "tests/**"
```

### Claude Code hooks: `.crucible/claudecode.yaml`

```yaml
on_finding: deny                    # deny, warn, allow
severity_threshold: error           # error, warning, info
run_assertions: true
run_llm_assertions: false
exclude:
  - "**/*.md"
  - "**/test_*.py"
```

### Review: `.crucible/review.yaml`

```yaml
fail_on: high
include_context: false              # Include findings near changes
```

---

## Next Steps

1. **Explore bundled assertions**: `crucible assertions list`
2. **Add your own rules**: `.crucible/assertions/`
3. **Customize personas**: `crucible skills init <skill>`
4. **Set up CI**: `crucible ci generate`

See [FEATURES.md](FEATURES.md) for the complete reference.
