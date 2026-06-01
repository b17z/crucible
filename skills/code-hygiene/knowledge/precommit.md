---
name: Pre-commit Hooks
description: Automated checks before commits - linting, formatting, secrets
triggers: [precommit, hooks, linting, formatting]
type: pattern
---

# Pre-commit Hook Principles

Automated guardrails before code enters the repo.

---

## Setup

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Initial scan
```

Config: `.pre-commit-config.yaml`

---

## Secret Detection (Critical)

Layer multiple scanners for defense-in-depth:

```yaml
repos:
  # Gitleaks - comprehensive secret scanner
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.1
    hooks:
      - id: gitleaks

  # Detect-secrets by Yelp - another layer
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  # Built-in checks
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: detect-aws-credentials
```

---

## Custom Secret Scanner

For high-confidence patterns:

```bash
HIGH_CONFIDENCE_PATTERNS=(
    # AWS
    'AKIA[0-9A-Z]{16}'

    # GitHub tokens
    'ghp_[A-Za-z0-9]{36}'
    'gho_[A-Za-z0-9]{36}'

    # API keys
    'sk-[A-Za-z0-9]{48}'           # OpenAI
    'sk-ant-[A-Za-z0-9\-]{80,}'    # Anthropic

    # Private keys
    '-----BEGIN (RSA |EC )?PRIVATE KEY-----'

    # Database URLs with passwords
    'postgres://[^:]+:[^@]+@'
    'mongodb://[^:]+:[^@]+@'
)
```

---

## Python Hooks

```yaml
# Ruff - fast linter
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.3.0
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format

# MyPy - type checking
- repo: https://github.com/pre-commit/mirrors-mypy
  rev: v1.8.0
  hooks:
    - id: mypy
      additional_dependencies: [types-all]
      args: [--strict]
```

---

## File Hygiene

```yaml
- repo: https://github.com/pre-commit/pre-commit-hooks
  rev: v4.5.0
  hooks:
    - id: trailing-whitespace
    - id: end-of-file-fixer
    - id: check-yaml
    - id: check-json
    - id: check-toml
    - id: check-added-large-files
      args: ['--maxkb=500']
    - id: check-merge-conflict
```

---

## Commit Message Validation

```yaml
- repo: https://github.com/commitizen-tools/commitizen
  rev: v3.13.0
  hooks:
    - id: commitizen
      stages: [commit-msg]
```

Enforces semantic commit format: `(type): description`

---

## CI Integration

```yaml
ci:
  autofix_commit_msg: |
    [pre-commit.ci] auto fixes from hooks
  autofix_prs: true
  autoupdate_schedule: weekly
```

---

## Skip Patterns

Files to exclude from scanning:

```bash
SKIP_PATTERNS=(
    '\.lock$'
    'package-lock\.json$'
    '\.min\.js$'
    'vendor/'
    'node_modules/'
)
```

---

## Blocked Commit Response

```
============================================================
COMMIT BLOCKED: Potential secrets detected!
============================================================

If these are false positives, you can:
  1. Add patterns to .gitignore
  2. Use 'git commit --no-verify' (NOT RECOMMENDED)
  3. Add file to hooks/secrets-allowlist.txt
```

---

## Anti-patterns

```yaml
# Bad: no secret detection
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace

# Bad: single layer of detection
# (one tool might miss what another catches)

# Bad: skipping hooks in CI
skip: [gitleaks, detect-secrets]

# Bad: loose file size limits
args: ['--maxkb=10000']
```

---

*Pair with comprehensive .gitignore for defense-in-depth.*
