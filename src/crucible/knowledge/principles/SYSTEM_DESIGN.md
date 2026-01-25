# System Design Principles

Start simple. Earn complexity.

---

## Start Monolith, Earn Microservices

```
Day 1 instinct:  "Let's use microservices!"
Reality:         You have 1 user and 3 endpoints.

The Path:
├── Start: Monolith (one deployable, one database)
├── Scale: Modular monolith (clear boundaries, could split)
├── Split: Microservices (only when you MUST)

When to split:
├── Teams stepping on each other
├── Genuinely different scaling needs
├── Regulatory isolation requirements
└── NOT because "Netflix does it"
```

---

## The Boring Architecture

For most apps, this is all you need:

```
┌─────────────────────────────────────────────────┐
│                    Client                        │
│            (Web / Mobile / CLI)                  │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                 API Layer                        │
│         (Next.js API / tRPC / REST)             │
└─────────────────────┬───────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌─────────────┐ ┌───────────┐ ┌───────────────┐
│  Database   │ │   Cache   │ │  File Storage │
│ (Postgres)  │ │  (Redis)  │ │     (S3)      │
└─────────────┘ └───────────┘ └───────────────┘
```

Add complexity only when you hit real limits.

---

## Stateless by Default

App servers should hold no state.

```
❌ Stateful:
├── Session stored in server memory
├── Uploaded files on local disk
├── In-memory cache per instance
└── Breaks when you add a second server

✅ Stateless:
├── Session in database or JWT
├── Files in S3/object storage
├── Cache in Redis (shared)
└── Any server can handle any request
```

**Why:** Servers die. Deploys replace them. State should survive.

---

## Horizontal vs Vertical Scaling

```
Vertical (scale up):
├── Bigger server
├── Simple, no code changes
└── START HERE

Horizontal (scale out):
├── More servers
├── Needs stateless design
└── DO THIS LATER (if ever)
```

**Reality:** A single Postgres handles millions of rows. You're not Google.

---

## Queue Everything That Can Wait

```
Synchronous: User waits for result
Asynchronous: User doesn't wait, can retry

Queue candidates:
├── Emails / notifications
├── Image processing
├── Report generation
├── Third-party API calls
└── Anything that can fail
```

---

## Cache Strategically

```
Cache when:
├── Read-heavy, write-light
├── Expensive to compute
├── Doesn't change often
├── Stale data is acceptable

Don't cache when:
├── Data changes constantly
├── Consistency is critical
├── It's already fast enough
```

**Invalidation is hard.** Start simple: time-based expiry.

---

## Idempotency

If it can be retried, it should be safe to retry.

```typescript
// ❌ Dangerous: double-charge if retried
stripe.charge(userId, amount);

// ✅ Idempotent: same result if called twice
stripe.charge(userId, amount, { idempotencyKey });
```

---

## Fail Gracefully

```
Design for failure:
├── External APIs will go down
├── Database will be slow sometimes
├── Your code has bugs

Strategies:
├── Timeouts on everything
├── Retries with backoff
├── Circuit breakers
├── Graceful degradation
└── Health checks
```

---

*Template. Adapt to your scale.*
