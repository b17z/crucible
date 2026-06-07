---
name: Functional Programming
description: Immutability, pure functions, composition patterns
triggers: [functional, fp, immutable, pure-functions]
type: preference
---

# Functional Programming Principles

---

## Core Concepts

```
FP characteristics:
├── Pure functions (same input → same output)
├── Immutable data structures
├── Functions as first-class values
├── Composition over inheritance
└── Side effects isolated to boundaries

Use OOP when:
├── Modeling stateful entities
├── Complex state machines
├── Framework requires it
```

---

## Pure Functions

Same input produces same output. No side effects.

```typescript
// Pure: No state access, no external calls
function calculateFee(amount: Cents): Cents {
  return Math.round(amount * 0.01) as Cents;
}

// Impure: Reads external state
function calculateFee(amount: Cents): Cents {
  return Math.round(amount * config.feeRate) as Cents;
}
```

---

## Immutability

```typescript
// Mutation (avoid)
const addItem = (items: Item[], newItem: Item) => {
  items.push(newItem); // Mutates original
  return items;
}

// Immutable (prefer)
const addItem = (items: Item[], newItem: Item): Item[] => {
  return [...items, newItem]; // New array
}
```

**In Python:**
```python
@dataclass(frozen=True)
class User:
    id: str
    email: str
```

---

## Composition Over Inheritance

```typescript
// Inheritance (rigid hierarchy)
class Animal { }
class Dog extends Animal { }
class ServiceDog extends Dog { }

// Composition (flexible)
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
// Class-based
class TipService {
  private db: Database;
  constructor(db: Database) { this.db = db; }
  async createTip(data: TipData) { ... }
}

// Function-based
const createTip = (db: Database, data: TipData): Promise<Result<Tip, TipError>> => { ... }

// Factory for grouping related functions
const createTipService = (db: Database) => ({
  create: (data: TipData) => createTip(db, data),
  getByPage: (pageId: PageId) => getTipsByPage(db, pageId),
});
```

---

## Data Transformations

Pipelines over loops:

```typescript
// Imperative
const results = [];
for (const user of users) {
  if (user.isActive) {
    results.push(user.email);
  }
}

// Declarative
const activeEmails = users
  .filter(user => user.isActive)
  .map(user => user.email);
```

---

## Side Effects at the Edges

Push side effects to the boundaries:

```
┌─────────────────────────────────────────────────────────┐
│  EDGES (side effects)                                    │
│  HTTP handlers, database calls, external APIs           │
└───────────────────────────┬─────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  CORE (pure)                                             │
│  Business logic, calculations, transformations          │
└─────────────────────────────────────────────────────────┘
```

---

*Template. Adapt to your needs.*
