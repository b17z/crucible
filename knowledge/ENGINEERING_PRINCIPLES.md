# Engineering Principles — Building Systems That Last

*How I build systems that scale, last, and don't make me hate my life.*

---

## Core Philosophy

```
1. Ship over perfection
2. Boring technology wins
3. Complexity is debt
4. Future me is a stranger — write code he can read
```

### The Meta-Principles

| Principle | Why |
|-----------|-----|
| **Boring is good** | Proven tech, known failure modes |
| **Complexity is debt** | Every abstraction has a cost |
| **Ship incrementally** | Small changes, fast feedback |
| **Design for change** | Requirements WILL change |
| **Future you is a stranger** | Write code they can understand at 2am |

---

## What MVP Actually Means

```
Minimum VIABLE Product:
├── Minimum: Smallest feature set that delivers value
├── Viable: Actually works. People can use it.
├── Product: Solves a real problem end-to-end

The key word is VIABLE.
├── Not "minimum possible effort"
├── Not "barely functional"
├── Not "works on my machine"
└── VIABLE = Someone would pay for this
```

### The Test:

```
"Would I be embarrassed if 100 people used this tomorrow?"

If yes → not ready
If no  → ship it
```

---

## Code Design

### Functional First

Default to FP. OOP has its place, but it's not the default.

```
Why FP:
├── Pure functions are testable
├── No hidden state to debug at 3am
├── Compose small things into big things
├── Easier to reason about
└── Parallelizes naturally

OOP when:
├── Genuinely modeling stateful entities
├── Complex state machines
├── Framework requires it
└── Actually makes the code simpler (rare)
```

**The Test:** "Could this just be a function?" — usually yes.

---

## Type Safety

### Discriminated Unions

```typescript
// ❌ Boolean flags
type Response = {
  loading: boolean;
  error: Error | null;
  data: Data | null;
}
// What if loading=true AND error is set?

// ✅ Discriminated union
type Response =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: Data };

// Only valid states are representable
```

---

## Error Handling

### Errors as Values, Not Exceptions

Don't throw. Return.

```typescript
// ✅ Result type
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

## Security

### Defense in Depth

Layer your defenses. Never rely on a single check.

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

## The Decision Framework

```
1. What's the simplest thing that works?
2. What's the most boring option?
3. What will I understand in 6 months?
4. What has the best failure modes?
5. What can I change later?

Usually, the answer to all five is the same thing.
```

---

## What I Don't Do

```
├── Microservices on day 1
├── Kubernetes for a CRUD app
├── NoSQL when Postgres works fine
├── GraphQL for internal APIs
├── Event sourcing without a reason
├── OOP by default
├── Any types
├── Throwing exceptions for control flow
├── Premature optimization
└── "It works on my machine"
```

---

## Final Word

```
The best code is code you don't have to think about.

It's obvious.
It's boring.
It works.
It's been working for months.

Nobody talks about it.
That's the goal.
```
