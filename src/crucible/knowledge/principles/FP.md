# Functional Programming Principles

> **Note:** This is an opinionated template favoring FP patterns.
> OOP has its place, but it's not the default.

---

## Core Philosophy

```
Default to FP. OOP when it genuinely simplifies.

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

## Pure Functions

Same input → same output. No side effects.

```typescript
// ✅ Pure: No state access, no external calls
function calculateFee(amount: Cents): Cents {
  return Math.round(amount * 0.01) as Cents;
}

// ❌ Impure: Reads external state
function calculateFee(amount: Cents): Cents {
  return Math.round(amount * config.feeRate) as Cents; // Depends on external state
}
```

---

## Immutability

```typescript
// ❌ Mutation
const addItem = (items: Item[], newItem: Item) => {
  items.push(newItem); // Mutates original
  return items;
}

// ✅ Immutable
const addItem = (items: Item[], newItem: Item): Item[] => {
  return [...items, newItem]; // New array
}
```

**In Python:**
```python
# ✅ Frozen dataclasses
@dataclass(frozen=True)
class User:
    id: str
    email: str
```

---

## Composition Over Inheritance

```typescript
// ❌ Inheritance (rigid)
class Animal { }
class Dog extends Animal { }
class ServiceDog extends Dog { }

// ✅ Composition (flexible)
const withLogging = (fn) => (...args) => {
  console.log('Called with:', args);
  return fn(...args);
};

const withRetry = (fn, attempts = 3) => async (...args) => {
  for (let i = 0; i < attempts; i++) {
    try { return await fn(...args); }
    catch (e) { if (i === attempts - 1) throw e; }
  }
};

// Compose behaviors
const resilientFetch = withRetry(withLogging(fetch));
```

---

## Functions vs Classes

```typescript
// ❌ OOP as default (verbose, tightly coupled)
class TipService {
  private db: Database;
  constructor(db: Database) { this.db = db; }
  async createTip(data: TipData) { ... }
}

// ✅ FP style (simple, composable, testable)
const createTip = (db: Database, data: TipData): Promise<Result<Tip, TipError>> => { ... }

// ✅ Factory for grouping related functions (when needed)
const createTipService = (db: Database) => ({
  create: (data: TipData) => createTip(db, data),
  getByPage: (pageId: PageId) => getTipsByPage(db, pageId),
});
```

---

## Data Transformations

Pipelines over loops:

```typescript
// ❌ Imperative
const results = [];
for (const user of users) {
  if (user.isActive) {
    results.push(user.email);
  }
}

// ✅ Declarative
const activeEmails = users
  .filter(user => user.isActive)
  .map(user => user.email);
```

---

## Side Effects at the Edges

Push side effects to the boundaries:

```
┌─────────────────────────────────────────────────────────┐
│  EDGES (side effects OK)                                 │
│  HTTP handlers, database calls, external APIs           │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  CORE (pure)                                             │
│  Business logic, calculations, transformations          │
│  No side effects. Easy to test.                         │
└─────────────────────────────────────────────────────────┘
```

---

*Opinionated template. Adjust for team preferences.*
