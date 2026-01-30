---
name: Type Safety
description: Type annotations, generics, strict mode, type guards
triggers: [types, typescript, typing, mypy, type-safety]
type: principle
---

# Type Safety Principles

Patterns for making invalid states unrepresentable.

---

## No `any`

```typescript
// any (defeats the purpose of TypeScript)
const process = (data: any) => { ... }

// unknown + narrowing
const process = (data: unknown) => {
  if (typeof data === 'string') {
    // TypeScript knows it's a string here
  }
}
```

---

## Branded Types

Prevent mixing up similar primitives:

```typescript
// Easy to mix up
const createTip = (pageId: string, amount: number) => { ... }
// createTip(tipId, pageId) compiles but is wrong!

// Branded types
type PageId = string & { readonly _brand: 'PageId' };
type TipId = string & { readonly _brand: 'TipId' };
type Cents = number & { readonly _brand: 'Cents' };

const createTip = (pageId: PageId, amount: Cents) => { ... }
// createTip(tipId, pageId) → Type error!
```

---

## Discriminated Unions

Make invalid states unrepresentable:

```typescript
// Boolean flags (invalid states possible)
type Response = {
  loading: boolean;
  error: Error | null;
  data: Data | null;
}
// What if loading=true AND error is set?

// Discriminated union (only valid states)
type Response =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: Data };
```

---

## Zod at Boundaries

Validate external data, then trust the types:

```typescript
import { z } from 'zod';

const TipSchema = z.object({
  pageId: z.string().uuid(),
  amountCents: z.number().int().positive().max(100000),
  message: z.string().max(500).optional(),
});

type Tip = z.infer<typeof TipSchema>;

// Validate at API boundary
const handler = (req: Request) => {
  const result = TipSchema.safeParse(req.body);
  if (!result.success) {
    return { error: result.error };
  }
  // result.data is fully typed and validated
  return createTip(result.data);
};
```

---

## Exhaustiveness Checking

TypeScript tells you when you miss a case:

```typescript
type Status = 'pending' | 'active' | 'cancelled';

const getLabel = (status: Status): string => {
  switch (status) {
    case 'pending': return 'Pending';
    case 'active': return 'Active';
    // TypeScript error: 'cancelled' not handled
  }
};

// Force exhaustiveness with never
const assertNever = (x: never): never => {
  throw new Error(`Unexpected: ${x}`);
};

const getLabel = (status: Status): string => {
  switch (status) {
    case 'pending': return 'Pending';
    case 'active': return 'Active';
    case 'cancelled': return 'Cancelled';
    default: return assertNever(status);
  }
};
```

---

## Strict Mode

Always enable:

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noUncheckedIndexedAccess": true
  }
}
```

---

## Optional vs Required

Be explicit:

```typescript
// Ambiguous
interface User {
  name: string;
  email: string;
  phone: string; // Required? Or just always present?
}

// Explicit
interface User {
  name: string;
  email: string;
  phone?: string; // Optional
}
```

---

*Template. Adapt to your needs.*
