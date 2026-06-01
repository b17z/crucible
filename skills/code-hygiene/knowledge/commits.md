---
name: Commit Messages
description: Conventional commits format and best practices
triggers: [git, commits, version-control]
type: pattern
---

# Commit Message Principles

Semantic commits for readable history.

---

## Format

```
(type): description

Body (optional)

Co-Authored-By: Name <email>
```

---

## Types

| Type | Use When |
|------|----------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code restructure (no behavior change) |
| `test` | Adding or updating tests |
| `chore` | Build, deps, config changes |
| `perf` | Performance improvement |
| `style` | Formatting, whitespace |

---

## Good Examples

```bash
# Feature
(feat): add pagination to tips endpoint

# Bug fix
(fix): handle empty response from Stripe webhook

# Refactor
(refactor): extract fee calculation to pure function

# Docs
(docs): add API authentication examples

# Test
(test): add integration tests for payment flow
```

---

## Bad Examples

```bash
# Too vague
fix stuff
update code
changes

# Too long
(feat): add a new endpoint for handling user authentication with OAuth2 and also add rate limiting and logging

# Wrong type
(feat): fix typo in README  # should be (docs) or (fix)
```

---

## Commit Body

For complex changes, add context:

```bash
(fix): prevent duplicate charges on retry

Stripe webhook was being processed multiple times when
the initial response timed out. Added idempotency check
using the event ID.

Closes #123
```

---

## Atomic Commits

One logical change per commit:

```
# Good: atomic commits
(feat): add User model
(feat): add user registration endpoint
(test): add user registration tests

# Bad: everything at once
(feat): add user feature
```

---

## Squashing

For feature branches with messy history:

```bash
# Interactive rebase before merge
git rebase -i main

# Squash WIP commits into meaningful ones
pick abc1234 (feat): add payment processing
squash def5678 WIP
squash ghi9012 fix tests
```

---

*Template. Adapt format to your team's conventions.*
