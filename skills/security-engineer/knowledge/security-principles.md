---
name: Security Principles
description: Core security principles - input validation, secrets, injection prevention
triggers: [security, auth, crypto, api, secrets, injection]
type: principle
assertions: security.yaml
---

# Security Principles

Quick reference for secure code patterns.

---

## Review Checklist

```
[ ] Dependencies updated (npm audit, pip audit)
[ ] No secrets in code or logs
[ ] Input validation on all endpoints
[ ] Rate limiting on sensitive routes
[ ] HTTPS everywhere
[ ] Auth on protected routes
[ ] CORS configured correctly
[ ] CSP headers set
[ ] SQL injection impossible (ORM/parameterized)
[ ] XSS prevented (escaped output)
[ ] CSRF tokens on forms
[ ] Audit logging for sensitive operations
```

---

## Input Validation

Validate at every trust boundary.

```typescript
const handler = (req: Request) => {
  const result = InputSchema.safeParse(req.body);
  if (!result.success) {
    return Response.json({ error: 'Invalid input' }, { status: 400 });
  }
  // Proceed with validated data
};
```

---

## Query Safety

```typescript
// SQL injection risk
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// Parameterized (ORMs do this automatically)
const user = await prisma.user.findUnique({ where: { id: userId } });
```

---

## Secrets Management

```
├── Env vars, not in code
├── Rotate on any suspected leak
├── Mask secrets in logs
├── Different secrets per environment
└── Use secret managers in production
```

---

## Defense in Depth

```
┌─────────────────────────────────────────────────────────┐
│  PREVENTION                                              │
│  Input validation, auth checks, rate limiting           │
└───────────────────────────┬─────────────────────────────┘
                            │ if prevention fails
                            ▼
┌─────────────────────────────────────────────────────────┐
│  DETECTION                                               │
│  Logging, monitoring, alerts, anomaly detection         │
└───────────────────────────┬─────────────────────────────┘
                            │ when detected
                            ▼
┌─────────────────────────────────────────────────────────┐
│  RESPONSE                                                │
│  Incident runbook, secret rotation, access revocation   │
└───────────────────────────┬─────────────────────────────┘
                            │ after response
                            ▼
┌─────────────────────────────────────────────────────────┐
│  RECOVERY                                                │
│  Backups, audit trail, rollback, post-mortem            │
└─────────────────────────────────────────────────────────┘
```

---

## Deserialization Safety

Do not deserialize untrusted data into objects that can execute code.

| Library | Dangerous | Safe Alternative |
|---------|-----------|------------------|
| Python | `pickle.load()`, `eval()` | `json.load()` |
| PyYAML | `yaml.load()` | `yaml.safe_load()` |
| subprocess | `shell=True` + user input | `shell=False`, explicit args |

**Principle:** If it can reconstruct arbitrary objects, it can execute arbitrary code.

---

## File Permissions & Path Safety

### Secure File Permissions

```python
# For sensitive files (keys, tokens, credentials)
import os
fd = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)  # Owner rw only
with os.fdopen(fd, 'w') as f:
    f.write(secret_data)

# For sensitive directories
os.makedirs(path, mode=0o700, exist_ok=True)  # Owner rwx only

# Permission reference
# 0o600 - Owner read/write (secrets, keys)
# 0o700 - Owner read/write/execute (sensitive dirs)
# 0o644 - Owner rw, others read (public files)
# 0o755 - Owner rwx, others rx (public dirs)
```

### Path Traversal Prevention

```python
# DANGEROUS - user input can escape directory
user_file = request.args.get('file')
path = f"/data/{user_file}"  # "../../../etc/passwd" escapes!

# SAFE - resolve and validate
from pathlib import Path
base = Path("/data").resolve()
user_path = (base / user_file).resolve()
if not str(user_path).startswith(str(base)):
    raise ValueError("Path traversal attempt")
```

---

## Risk Surface Mapping

```
Step 1: Map Data Flows
├── Where does data come from?
├── Where does it go?
├── Who can access it?
└── What's the impact if wrong/leaked/lost?

Step 2: Categorize Risks
├── Data Integrity     → Wrong data stored
├── Confidentiality    → Sensitive data exposed
├── Auth Bypass        → Unauthorized access
├── Injection          → SQL, XSS, command injection
├── Path Traversal     → Access to unintended files
└── Denial of Service  → Resource exhaustion
```

---

*Template. Adapt to your needs.*
