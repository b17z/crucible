---
name: Database Patterns
description: Migrations, indexing, query patterns, connection management
triggers: [database, sql, postgres, mysql, migrations]
type: pattern
---

# Database Principles

---

## Core Rules

| Rule | Reason |
|------|--------|
| UUIDs for primary keys | No enumeration attacks, no auto-increment collisions |
| Timestamps on everything | `created_at`, `updated_at` for debugging |
| Soft delete when data matters | `deleted_at` instead of hard delete |
| Amounts in cents | No floating point money (500 = $5.00) |
| Encrypt sensitive data at rest | Defense in depth |

---

## Index Strategy

```sql
-- Every foreign key
CREATE INDEX idx_tips_page_id ON tips(page_id);

-- Everything you WHERE on
CREATE INDEX idx_profiles_username ON user_profiles(username);

-- Everything you ORDER BY
CREATE INDEX idx_tips_created_at ON tips(created_at);

-- Composite for common query patterns
CREATE INDEX idx_tips_page_status ON tips(page_id, status);
```

---

## Optimization Order

```
1. Indexes (90% of performance issues)
2. Query design (N+1, unbounded selects)
3. Connection pooling
4. Read replicas
5. Caching layer
6. Sharding (rarely needed)
```

---

## N+1 Queries

```typescript
// N+1 (1 query for pages + N queries for tips)
const pages = await db.page.findMany();
for (const page of pages) {
  const tips = await db.tip.findMany({ where: { pageId: page.id } });
}

// Include (1 query with join)
const pages = await db.page.findMany({
  include: { tips: true }
});
```

---

## Naming Conventions

```
Tables:  plural, snake_case     → user_profiles, orders
Columns: snake_case             → created_at, user_id
Indexes: descriptive            → idx_tips_page_id
```

---

## Migrations

```
├── One migration per change
├── Migrations should be reversible
├── Test migrations on production data (copy)
├── Do not edit deployed migrations
└── Separate schema changes from data migrations
```

---

## Transactions

```typescript
// Atomic operations
await db.$transaction(async (tx) => {
  await tx.account.update({
    where: { id: fromAccount },
    data: { balance: { decrement: amount } }
  });
  await tx.account.update({
    where: { id: toAccount },
    data: { balance: { increment: amount } }
  });
});
// Both succeed or both fail
```

---

## Connection Pooling

```
├── Use connection pools (Prisma does this)
├── Size pool based on: (cores * 2) + disk spindles
├── Set connection timeout
├── Monitor pool exhaustion
```

---

## Query Safety

Use parameterized queries:

```typescript
// SQL injection risk
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// Parameterized (ORMs do this)
const user = await db.user.findUnique({ where: { id: userId } });
```

---

*Template. Adapt to your needs.*
