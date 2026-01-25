# Error Handling Principles

Errors as values, not exceptions.

---

## Core Philosophy

Don't throw. Return.

```typescript
// ❌ Throwing (invisible control flow)
const getUser = (id: UserId): User => {
  const user = db.find(id);
  if (!user) throw new Error('Not found');
  return user;
}

// ✅ Result type (explicit, type-safe)
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

const getUser = (id: UserId): Result<User, 'NOT_FOUND' | 'DB_ERROR'> => {
  try {
    const user = db.find(id);
    if (!user) return { ok: false, error: 'NOT_FOUND' };
    return { ok: true, value: user };
  } catch (e) {
    return { ok: false, error: 'DB_ERROR' };
  }
}
```

---

## Caller Must Handle

```typescript
const result = await getUser(id);
if (!result.ok) {
  // Handle error - can't forget!
  return;
}
// result.value is typed as User
```

---

## Typed Errors

```typescript
// ❌ String errors (no structure, no exhaustiveness checking)
throw new Error('Something went wrong');

// ✅ Typed errors (structured, exhaustive)
type TipError =
  | { type: 'PAGE_NOT_FOUND' }
  | { type: 'AMOUNT_TOO_SMALL'; minimum: Cents }
  | { type: 'AMOUNT_TOO_LARGE'; maximum: Cents }
  | { type: 'PAYMENT_FAILED'; reason: string };

const handleError = (error: TipError) => {
  switch (error.type) {
    case 'PAGE_NOT_FOUND':
      return 'Page not found';
    case 'AMOUNT_TOO_SMALL':
      return `Minimum amount is ${error.minimum}`;
    // TypeScript ensures all cases handled
  }
};
```

---

## When to Throw

Exceptions are for **truly exceptional** things:

```
Throw for:
├── Out of memory
├── Network unreachable
├── Programmer errors (assertions, invariant violations)
├── API boundaries (convert Result → HTTP status)

Don't throw for:
├── Business logic ("user not found" is expected)
├── Validation errors
├── Anything the caller should handle
```

---

## Python Pattern

```python
from dataclasses import dataclass
from typing import Union

@dataclass(frozen=True)
class Ok[T]:
    value: T

@dataclass(frozen=True)
class Err[E]:
    error: E

Result = Union[Ok[T], Err[E]]

def get_user(user_id: str) -> Result[User, str]:
    user = db.find(user_id)
    if not user:
        return Err("NOT_FOUND")
    return Ok(user)
```

---

## Error Messages

```typescript
// ❌ Vague
throw new Error('Failed');

// ✅ Actionable
throw new Error(`Failed to fetch user ${userId}: connection timeout after 5000ms`);
```

---

## Never Swallow Errors

```typescript
// ❌ Silent failure
try {
  await riskyOperation();
} catch (e) {
  // nothing
}

// ✅ At minimum, log
try {
  await riskyOperation();
} catch (e) {
  log.error('riskyOperation failed', { error: e });
  // Then decide: rethrow, return default, or return error
}
```

---

*Template. Adapt Result type to your language/framework.*
