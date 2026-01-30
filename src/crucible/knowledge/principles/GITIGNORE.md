---
name: Gitignore Patterns
description: What to exclude from version control
triggers: [gitignore, git, secrets]
type: pattern
---

# Gitignore Principles

Defense-in-depth for preventing secret commits.

---

## Structure

Organize by category with clear headers:

```gitignore
# ============================================================================
# SECRETS & SENSITIVE FILES (NEVER COMMIT)
# ============================================================================

# Environment files
.env
.env.*
!.env.example

# Private keys & certificates
*.pem
*.key
*.p12
```

---

## Secrets (Critical)

### Environment Files

```gitignore
.env
.env.*
*.env
*.env.*
!.env.example
!.env.*.example
.envrc
.envrc.*
*.local
```

### Private Keys

```gitignore
*.pem
*.key
*.p12
*.pfx
*.jks
*.crt
id_rsa*
id_ed25519*
*.gpg
*.asc
```

### Credentials

```gitignore
credentials.json
secrets.json
service-account*.json
*-keyfile.json
*.secret
*.credentials
application_default_credentials.json
```

### Cloud Configs

```gitignore
.aws/
.gcloud/
.azure/
*.tfstate
*.tfvars
```

---

## Paranoid Mode

Catch-all patterns for defense-in-depth:

```gitignore
# Anything with "secret" in the name
*secret*
*SECRET*
!hooks/*-secrets.sh  # Allow hook scripts

# Anything with "password" in the name
*password*
*PASSWORD*

# Anything with "credential" in the name
*credential*
*CREDENTIAL*

# Anything with "private" in the name
*_private.*
*.private.*
```

---

## OS & Editor

```gitignore
# macOS
.DS_Store
._*

# Windows
Thumbs.db
Desktop.ini

# IDEs (allow shared settings)
.vscode/
!.vscode/settings.json
!.vscode/extensions.json
.idea/

# Vim
*.swp
*.swo
```

---

## Dependencies by Language

```gitignore
# Node
node_modules/
.pnpm-store/

# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Go
vendor/

# Rust
target/
```

---

## Build & Test Output

```gitignore
dist/
build/
out/
coverage/
htmlcov/
.coverage
*.log
```

---

## Tool-Specific

```gitignore
# Terraform (SECRETS!)
.terraform/
*.tfstate*
*.tfvars

# Docker
docker-compose.override.yml

# Kubernetes
*.kubeconfig
*-secret.yaml
```

---

## Anti-patterns

```gitignore
# Bad: too broad
*

# Bad: no exceptions for examples
.env*

# Bad: missing paranoid patterns
# (relies only on specific patterns)

# Bad: no structure
.env
node_modules
*.log
.DS_Store
```

---

*Layer with pre-commit hooks for defense-in-depth.*
