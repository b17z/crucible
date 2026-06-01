---
name: System Design
description: Architecture patterns, scalability, distributed systems
triggers: [architecture, system-design, scalability, distributed]
type: principle
---

# System Design Principles

---

## Monolith to Microservices

```
Progression:
├── Monolith: One deployable, one database
├── Modular monolith: Clear boundaries, could split
├── Microservices: Multiple deployables, distributed

Indicators to split:
├── Teams blocked by shared codebase
├── Components have different scaling requirements
├── Regulatory isolation required
└── Deployment coupling causes issues
```

---

## Reference Architecture

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

---

## Stateless Servers

App servers should hold no state.

```
Stateful patterns (avoid):
├── Session stored in server memory
├── Uploaded files on local disk
├── In-memory cache per instance
└── Breaks on horizontal scaling

Stateless patterns:
├── Session in database or JWT
├── Files in S3/object storage
├── Cache in Redis (shared)
└── Any server can handle any request
```

---

## Scaling

```
Vertical (scale up):
├── Larger server instance
├── No code changes required
└── Simpler to operate

Horizontal (scale out):
├── Multiple server instances
├── Requires stateless design
└── More complex to operate
```

---

## Async Processing

```
Queue candidates:
├── Emails / notifications
├── Image processing
├── Report generation
├── Third-party API calls
└── Any operation that can fail and retry
```

---

## Caching

```
Good candidates:
├── Read-heavy, write-light data
├── Expensive to compute
├── Infrequent changes
├── Stale data acceptable

Poor candidates:
├── Frequently changing data
├── Strong consistency required
├── Already fast enough
```

Invalidation strategies: time-based expiry, event-based invalidation, cache-aside pattern.

---

## Idempotency

Operations that can be retried should produce the same result.

```typescript
// Non-idempotent: double-charge on retry
stripe.charge(userId, amount);

// Idempotent: same result on retry
stripe.charge(userId, amount, { idempotencyKey });
```

---

## Failure Handling

```
Design assumptions:
├── External APIs will fail
├── Database latency will spike
├── Code has bugs

Strategies:
├── Timeouts on all external calls
├── Retries with exponential backoff
├── Circuit breakers
├── Graceful degradation
└── Health checks
```

---

*Template. Adapt to your needs.*
