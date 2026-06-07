---
name: Testing Principles
description: Test pyramid, unit/integration/e2e, mocking patterns
triggers: [testing, tests, unit-tests, integration, e2e]
type: principle
---

# Testing Principles

What to test, how to structure tests, and patterns that work.

---

## The Pyramid

```
        /\          Few E2E (critical paths only)
       /  \
      /────\        Some integration (API, DB)
     /      \
    /────────\      Many unit tests (fast, pure)
```

---

## What to Test

```
Test:
├── Business logic (core package)
├── Edge cases
├── Regression bugs (write test, then fix)
├── Complex calculations
└── State machines

Don't test:
├── Framework behavior
├── Third-party libraries
├── Implementation details
├── Things that change constantly (UI specifics)
└── Obvious code (getters, setters)
```

---

## FP Makes Testing Easy

Pure functions = same input, same output. No mocking needed.

```typescript
const calculateFee = (amount: Cents): Cents => {
  return Math.round(amount * 0.01) as Cents;
};

test('calculates 1% fee', () => {
  expect(calculateFee(1000 as Cents)).toBe(10);
  expect(calculateFee(999 as Cents)).toBe(10);
  expect(calculateFee(100 as Cents)).toBe(1);
});
```

---

## Test Naming

```typescript
// Vague
test('it works', () => { ... });

// Descriptive
test('calculateFee rounds up for fractional cents', () => { ... });
test('returns NOT_FOUND when user does not exist', () => { ... });
```

---

## Integration Tests

Test real behavior, not mocks.

```typescript
// Mocking everything
jest.mock('../database');
jest.mock('../stripe');
// What are you even testing?

// Test real behavior with test database
beforeEach(() => db.reset());
test('creates user in database', async () => {
  await createUser({ email: 'test@example.com' });
  const user = await db.user.findFirst({ where: { email: 'test@example.com' } });
  expect(user).not.toBeNull();
});
```

---

## Property-Based Testing

For invariants that should always hold:

```typescript
import fc from 'fast-check';

test('fee is always positive', () => {
  fc.assert(
    fc.property(fc.integer({ min: 1 }), (amount) => {
      return calculateFee(amount as Cents) >= 0;
    })
  );
});
```

---

## The Rule

```
If you find a bug:
1. Write a test that reproduces it
2. Watch it fail
3. Fix the bug
4. Watch it pass
5. Never have that bug again
```

---

*Template. Adapt to your needs.*
