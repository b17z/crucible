---
name: API Design
description: REST conventions, versioning, pagination, error responses
triggers: [api, rest, http, endpoints]
type: pattern
---

# API Design Principles

REST conventions, response shapes, and common patterns.

---

## REST Conventions

```
Nouns, not verbs:
├── GET    /tips         ← List tips
├── POST   /tips         ← Create tip
├── GET    /tips/:id     ← Get single tip
├── PUT    /tips/:id     ← Update tip (full)
├── PATCH  /tips/:id     ← Update tip (partial)
├── DELETE /tips/:id     ← Delete tip
```

---

## Consistent Response Shapes

```typescript
// Success
{ data: T }

// Error
{ error: { code: string, message: string } }

// List (with pagination)
{ data: T[], meta: { total: number, page: number, pageSize: number } }
```

---

## HTTP Status Codes

```
200 OK           ← Success (GET, PUT, PATCH)
201 Created      ← Resource created (POST)
204 No Content   ← Success, no body (DELETE)
400 Bad Request  ← Client error (validation)
401 Unauthorized ← Not authenticated
403 Forbidden    ← Authenticated but not allowed
404 Not Found    ← Resource doesn't exist
409 Conflict     ← State conflict
422 Unprocessable← Validation failed
429 Too Many     ← Rate limited
500 Server Error ← Server fault
```

---

## Rate Limiting

```
Headers to return:
├── X-RateLimit-Limit: 100
├── X-RateLimit-Remaining: 95
├── X-RateLimit-Reset: 1609459200
└── Retry-After: 60 (on 429)
```

---

## Pagination

Use bounded lists:

```typescript
// Request
GET /tips?page=2&pageSize=20

// Response
{
  data: [...],
  meta: {
    total: 150,
    page: 2,
    pageSize: 20,
    totalPages: 8
  }
}
```

---

## Versioning

```
For internal APIs (tRPC, same team):
├── No explicit versioning
├── Type system catches breakage
└── Change and deploy together

For public APIs (external consumers):
├── Version in URL: /v1/tips
├── Support N-1 version minimum
├── Deprecation warnings before removal
└── Breaking change = major version bump
```

---

## Idempotency

For operations that can be retried:

```typescript
// Not idempotent
POST /payments
{ amount: 100 }
// Called twice = charged twice

// Idempotent
POST /payments
{
  amount: 100,
  idempotencyKey: "user-123-order-456"
}
// Called twice = charged once
```

---

## Error Responses

```typescript
// Vague
{ error: "Something went wrong" }

// Actionable
{
  error: {
    code: "VALIDATION_ERROR",
    message: "Invalid request",
    details: [
      { field: "email", message: "Must be a valid email" },
      { field: "amount", message: "Must be positive" }
    ]
  }
}
```

---

## tRPC for Internal APIs

Type-safe end-to-end:

```typescript
export const tipRouter = router({
  create: protectedProcedure
    .input(CreateTipSchema)
    .mutation(({ input, ctx }) => {
      return createTip(ctx.db, input);
    }),

  list: protectedProcedure
    .input(z.object({ pageId: z.string() }))
    .query(({ input }) => {
      return getTipsByPage(input.pageId);
    }),
});
```

---

*Template. Adapt to your needs.*
