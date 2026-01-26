# Customizing Crucible

Personas and knowledge cascade for project-specific patterns.

## The Cascade Pattern

Both skills and knowledge follow the same resolution pattern:

```
1. PROJECT    .crucible/skills/ or .crucible/knowledge/    (highest priority)
2. USER       ~/.claude/crucible/skills/ or knowledge/
3. BUNDLED    <package>/skills/ or knowledge/principles/   (lowest priority)
```

First found wins. This lets you:
- Override bundled defaults for a specific project
- Maintain personal preferences across all projects
- Fall back to bundled templates when no override exists

---

## Skills Customization

### See What's Available

```bash
crucible skills list
```

Shows skills from all three sources with their locations.

### Check Which Version is Active

```bash
crucible skills show security-engineer

security-engineer
  Project: (not set)
  User:    ~/.claude/crucible/skills/security-engineer/SKILL.md ← active
  Bundled: .../site-packages/crucible/skills/security-engineer/SKILL.md
```

### Install Bundled Skills to User Level

```bash
crucible skills install

# Or force overwrite existing
crucible skills install --force
```

Copies all bundled skills to `~/.claude/crucible/skills/`.

### Customize for a Project

```bash
crucible skills init security-engineer
```

Creates `.crucible/skills/security-engineer/SKILL.md` copied from the active version.

Now edit it to add project-specific concerns:

```yaml
# .crucible/skills/security-engineer/SKILL.md
---
version: "1.0"
triggers: [security, auth, secrets]
knowledge: [SECURITY.md]
---

# Security Engineer

## Project-Specific Concerns

- We use Auth0 for authentication
- All PII must be encrypted at rest
- Rate limit all public endpoints to 100/min

## Red Flags

[...bundled content plus your additions...]
```

---

## Knowledge Customization

### See What's Available

```bash
crucible knowledge list
```

Shows knowledge files from all sources.

### Check Which Version is Active

```bash
crucible knowledge show SECURITY

SECURITY.md
  Project: (not set)
  User:    (not installed)
  Bundled: .../knowledge/principles/SECURITY.md ← active
```

### Install to User Level

```bash
crucible knowledge install

# Or force overwrite
crucible knowledge install --force
```

### Customize for a Project

```bash
crucible knowledge init SECURITY
```

Creates `.crucible/knowledge/SECURITY.md`. Edit to add:

```markdown
# Security Principles

[...bundled content...]

---

## Project-Specific Security

### Auth Pattern
We use JWT with 15-minute access tokens and 7-day refresh tokens.
Store in httpOnly cookies, never localStorage.

### Secrets
All secrets in 1Password. Never commit to repo.
Use `op read` for local dev, env vars in production.

### PII Handling
- Encrypt all PII at rest (AES-256)
- Log user IDs, never emails or names
- GDPR: support data export and deletion
```

---

## Creating New Skills

For project-specific personas not in bundled set:

```bash
mkdir -p .crucible/skills/compliance-reviewer
```

```yaml
# .crucible/skills/compliance-reviewer/SKILL.md
---
version: "1.0"
triggers: [compliance, audit, regulatory, gdpr, hipaa]
knowledge: [SECURITY.md]
---

# Compliance Reviewer

You are reviewing code from a compliance perspective. Focus on regulatory requirements and audit trails.

## Key Questions

- Is PII handling GDPR compliant?
- Are audit logs sufficient for SOC2?
- Is data retention policy followed?
- Are access controls documented?

## Red Flags

- PII logged without masking
- Missing audit trail for data access
- Hardcoded retention periods
- No data deletion mechanism

## Before Approving

- [ ] PII is identified and protected
- [ ] Audit logs capture who/what/when
- [ ] Data retention is configurable
- [ ] Deletion requests can be fulfilled
```

---

## Creating New Knowledge

For project-specific engineering principles:

```bash
mkdir -p .crucible/knowledge
```

```markdown
# .crucible/knowledge/INTERNAL_APIS.md

# Internal API Patterns

Our internal API conventions.

---

## Authentication

All internal services use mTLS + service accounts.

```python
# Always verify caller
from internal_auth import verify_service
caller = verify_service(request.headers)
```

---

## Error Responses

Standard error shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human readable",
    "details": [...]
  },
  "request_id": "uuid"
}
```

---

## Rate Limits

| Service | Limit | Window |
|---------|-------|--------|
| Auth | 100/min | Per IP |
| API | 1000/min | Per token |
| Webhooks | 10/sec | Per endpoint |
```

Then link from your skills:

```yaml
# .crucible/skills/backend-engineer/SKILL.md
---
knowledge: [API_DESIGN.md, INTERNAL_APIS.md]  # Add your custom knowledge
---
```

---

## Workflow Examples

### Team Onboarding

1. Create `.crucible/` in repo
2. Customize skills for team conventions
3. Add project-specific knowledge
4. Commit to repo
5. New team members get your review standards automatically

### Personal Preferences

1. `crucible skills install` - get bundled skills
2. Edit `~/.claude/crucible/skills/*/SKILL.md`
3. Add your review style preferences
4. Works across all your projects

### Project Override

1. `crucible skills init tech-lead`
2. Add project architecture decisions
3. Now reviews consider your specific context
4. Bundled version still available as reference

---

## Gitignore Patterns

Typically commit `.crucible/` to share with team:

```gitignore
# Don't ignore - share with team
# .crucible/
```

If you have personal overrides in a shared repo:

```gitignore
# Personal overrides only
.crucible/skills/my-personal-skill/
```

---

## Tips

**Start minimal.** Don't customize everything. Override only what you need.

**Document why.** Add comments explaining why you changed something from the default.

**Keep bundled reference.** Run `crucible skills show <skill>` to see bundled path if you need to check original.

**Update periodically.** When crucible updates, review your customizations against new bundled versions.
