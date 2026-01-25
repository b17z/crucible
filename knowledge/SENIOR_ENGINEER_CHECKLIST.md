# Senior Engineer Review Checklist

**A general-purpose reference.** This document is not Backit-specific - it's a collection of questions, patterns, and feedback that senior/staff/principal engineers across different domains would raise during code review. Use this as a self-review checklist before shipping any production code.

**Related docs:**
- `ENGINEERING_PRINCIPLES.md` — The philosophy and "why" behind good engineering
- `ENGINEERING_SUGGESTIONS.md` — Backit-specific audit findings and implementation priorities

---

## How to Use This Document

Before shipping any feature touching critical paths (money, auth, data):

1. Pick the relevant domain sections below
2. Ask yourself each question
3. If you can't answer confidently, that's a gap to address
4. Document your answers in PR descriptions

---

## Security Engineer Perspective

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What's the threat model?" | Can't defend against undefined threats |
| "Where does untrusted input enter?" | All vulnerabilities start at input boundaries |
| "What's the blast radius if this fails?" | Determines how much defense is needed |
| "Can this be replayed?" | Idempotency prevents duplicate actions |
| "Who can call this and with what permissions?" | AuthZ gaps are common |
| "What gets logged and what shouldn't?" | PII/secrets in logs = breach |
| "Is this timing-safe?" | Timing attacks on auth are real |

### Red Flags They Spot Immediately

```typescript
// RED FLAG: User input in SQL/command
`SELECT * FROM users WHERE id = ${userId}`  // SQL injection
exec(`convert ${filename}`)                  // Command injection

// RED FLAG: Secrets in code
const API_KEY = "sk_live_abc123"            // Should be env var

// RED FLAG: Missing rate limiting on auth
app.post('/login', async (req, res) => {    // Brute force vulnerable
  // no rate limit check
})

// RED FLAG: Trusting client data for authorization
if (req.body.isAdmin) { /* grant admin */ } // Client controls this!

// RED FLAG: Logging sensitive data
console.log('User payment:', { card: req.body.cardNumber })
```

### What They Approve

- Defense in depth (multiple validation layers)
- Fail-secure defaults (deny by default)
- Principle of least privilege
- Input validation at every boundary
- Constant-time comparison for secrets
- Structured logging with redaction

### Security Review Template

```markdown
## Security Considerations

**Threat Model:**
- Who are the adversaries? (script kiddies, competitors, nation states)
- What do they want? (data, money, disruption)
- What's their capability? (automated scans, targeted attacks)

**Input Boundaries:**
- [ ] All user input validated
- [ ] All external API responses validated
- [ ] File uploads checked (type, size, content)

**Output Safety:**
- [ ] No secrets in logs
- [ ] No PII in error messages
- [ ] Proper escaping for context (HTML, SQL, shell)

**Access Control:**
- [ ] Authentication required where needed
- [ ] Authorization checked (not just "is logged in" but "can do this action")
- [ ] Rate limiting on sensitive endpoints
```

---

## Web3/Blockchain Engineer Perspective

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "Is this address checksummed?" | EIP-55 checksums catch typos |
| "What if the address is a contract?" | Contracts behave differently than EOAs |
| "Is this deterministic?" | Same inputs must produce same outputs |
| "What happens on reorg?" | Blocks can be reorganized |
| "Is the amount in wei or tokens?" | 18 decimals vs 6 decimals matters |
| "Who pays gas?" | UX and cost implications |

### Red Flags They Spot Immediately

```typescript
// RED FLAG: No checksum validation
const isValid = /^0x[a-fA-F0-9]{40}$/.test(addr)  // Format only!
// Better: use viem's isAddress() which validates checksum

// RED FLAG: Assuming token decimals
const amount = userInput * 1e18  // USDC is 6 decimals, not 18!

// RED FLAG: Floating point for money
const fee = amount * 0.01  // Floating point errors
// Better: use BigInt or dedicated library

// RED FLAG: Not handling reverts
await contract.transfer(to, amount)  // What if it reverts?

// RED FLAG: Hardcoded addresses
const TREASURY = "0x1234..."  // What if it changes? What network?

// RED FLAG: Missing slippage protection
await swap(tokenIn, tokenOut, amount)  // MEV sandwich attack
```

### What They Approve

```typescript
// GOOD: Using viem's type-safe address handling
import { isAddress, getAddress } from 'viem'

function validateAddress(addr: string): `0x${string}` {
  if (!isAddress(addr)) throw new Error('Invalid address')
  return getAddress(addr)  // Returns checksummed
}

// GOOD: Explicit decimal handling
const USDC_DECIMALS = 6
const amount = BigInt(userInput) * BigInt(10 ** USDC_DECIMALS)

// GOOD: Network-aware configuration
const TREASURY: Record<number, `0x${string}`> = {
  1: '0x...',      // mainnet
  8453: '0x...',   // base
}

// GOOD: Deterministic operations
// Same inputs → same split address (CREATE2)
const splitAddress = await predictImmutableSplitAddress({ recipients })
```

### Crypto-Specific Checklist

```markdown
## Web3 Review Checklist

**Address Handling:**
- [ ] Addresses validated with checksum (EIP-55)
- [ ] Addresses normalized consistently (lowercase for storage)
- [ ] Contract vs EOA distinction handled if relevant
- [ ] Network/chainId verified

**Token Handling:**
- [ ] Decimals handled correctly per token
- [ ] BigInt used for amounts (no floating point)
- [ ] Overflow checks in place

**Transaction Safety:**
- [ ] Revert cases handled
- [ ] Gas estimation includes buffer
- [ ] Nonce management for multiple txs
- [ ] Finality requirements documented (confirmations needed)

**Determinism:**
- [ ] Same inputs produce same outputs
- [ ] No reliance on block.timestamp for critical logic
- [ ] Reorg scenarios considered
```

---

## Backend/Systems Engineer Perspective

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What happens at 10x load?" | Scale breaks assumptions |
| "Is this idempotent?" | Retries shouldn't cause duplicates |
| "What's the failure mode?" | Graceful degradation vs hard failure |
| "Where's the single source of truth?" | Data consistency |
| "Is this query indexed?" | N+1 and full table scans |
| "What's the rollback plan?" | Migrations can fail |

### Red Flags They Spot Immediately

```typescript
// RED FLAG: N+1 query
const users = await db.user.findMany()
for (const user of users) {
  const posts = await db.post.findMany({ where: { userId: user.id }})
}
// Better: include or join

// RED FLAG: No idempotency key
app.post('/payment', async (req) => {
  await createPayment(req.body)  // Double-click = double charge
})

// RED FLAG: Business logic in multiple places
// validation.ts: if (amount < 200) throw
// controller.ts: if (amount < 200) return error
// client.ts: if (amount < 200) disable button
// Which is authoritative?

// RED FLAG: Implicit ordering dependency
await createUser()
await createWallet()  // What if createUser fails?
await sendWelcomeEmail()

// RED FLAG: Unbounded queries
const allLogs = await db.log.findMany()  // Could be millions
```

### What They Approve

```typescript
// GOOD: Explicit transaction boundaries
await db.$transaction(async (tx) => {
  const user = await tx.user.create({ ... })
  await tx.wallet.create({ userId: user.id, ... })
})

// GOOD: Idempotency keys
app.post('/payment', async (req) => {
  const existing = await db.payment.findUnique({
    where: { idempotencyKey: req.body.idempotencyKey }
  })
  if (existing) return existing  // Return cached result
  // ... create new payment
})

// GOOD: Single source of truth
// packages/core/src/constants.ts
export const MIN_TIP_CENTS = 200
// Used everywhere, changed in one place

// GOOD: Bounded queries with pagination
const logs = await db.log.findMany({
  take: 100,
  skip: offset,
  orderBy: { createdAt: 'desc' }
})
```

### Backend Review Template

```markdown
## Backend Review Checklist

**Data Integrity:**
- [ ] Transactions wrap related operations
- [ ] Idempotency keys for mutations
- [ ] Unique constraints on business keys
- [ ] Foreign keys enforced

**Performance:**
- [ ] Queries use indexes (check EXPLAIN)
- [ ] No N+1 queries
- [ ] Pagination on list endpoints
- [ ] Appropriate caching

**Reliability:**
- [ ] Graceful degradation for non-critical failures
- [ ] Retry logic with backoff for external calls
- [ ] Circuit breakers for downstream dependencies
- [ ] Health checks expose dependency status

**Observability:**
- [ ] Structured logging (JSON, not strings)
- [ ] Request IDs for tracing
- [ ] Metrics on business operations
- [ ] Alerts on error rate spikes
```

---

## DevOps/SRE Perspective

DevOps and Site Reliability Engineers think about operability, observability, and what happens at 3am.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "How do we know it's working?" | Can't fix what you can't see |
| "What's the runbook?" | Someone will debug this at 3am |
| "What's the blast radius?" | Failures should be contained |
| "How do we roll back?" | Every deploy needs an exit |
| "What's the SLO/SLI?" | Define "working" quantitatively |
| "Where are the logs?" | First thing you check in an incident |
| "What alerts exist?" | Proactive > reactive |

*Inspired by observability practitioners and SRE community wisdom.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: No structured logging
console.log('Error:', error)  // What service? What request? What context?

// RED FLAG: No request tracing
app.post('/payment', async (req) => {
  // No request ID, can't correlate across services
})

// RED FLAG: Silent failures
try { await sendEmail() } catch {}  // Failed silently, nobody knows

// RED FLAG: No health checks
// App starts but can't reach database - looks healthy, isn't

// RED FLAG: Hardcoded timeouts
await fetch(url)  // What's the timeout? What if it hangs?

// RED FLAG: No circuit breakers
for (const item of items) {
  await callExternalAPI(item)  // If API is down, you'll retry forever
}

// RED FLAG: Secrets in environment output
console.log('Config:', process.env)  // Leaks API keys to logs
```

### What They Approve

```typescript
// GOOD: Structured logging with context
const log = logger.child({
  service: 'payment',
  requestId: req.headers['x-request-id'],
  userId: session.userId
})
log.info('Payment initiated', { amount, currency })

// GOOD: Health checks with dependency status
app.get('/health', async () => {
  const db = await checkDatabase()
  const redis = await checkRedis()
  return { status: db && redis ? 'healthy' : 'degraded', db, redis }
})

// GOOD: Explicit timeouts
const response = await fetch(url, {
  signal: AbortSignal.timeout(5000)
})

// GOOD: Graceful degradation
const features = await getFeatureFlags().catch(() => DEFAULT_FLAGS)

// GOOD: Runbook links in alerts
// Alert: Payment processing latency > 5s
// Runbook: https://docs.company.com/runbooks/payment-latency
```

### SRE Review Template

```markdown
## SRE Review Checklist

**Observability:**
- [ ] Structured logging (JSON, not strings)
- [ ] Request IDs for tracing across services
- [ ] Metrics on business operations (not just HTTP codes)
- [ ] Dashboards for key flows

**Reliability:**
- [ ] Health checks expose dependency status
- [ ] Graceful degradation for non-critical failures
- [ ] Timeouts on all external calls
- [ ] Circuit breakers for downstream dependencies

**Operability:**
- [ ] Runbook exists for common failure modes
- [ ] Rollback plan documented
- [ ] Alerts have clear severity and ownership
- [ ] On-call knows how to respond

**Deployment:**
- [ ] Feature flags for risky changes
- [ ] Canary/gradual rollout possible
- [ ] Database migrations are reversible
```

### SRE Sayings

> "If it's not in the logs, it didn't happen."

> "Your monitoring is only as good as your worst incident."

> "Hope is not a strategy. Automation is."

> "The best incident is the one that never becomes an outage."

---

## Product Engineer Perspective

Product engineers think about user value, not just code correctness. They bridge engineering and product.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What problem does this solve?" | Code without purpose is waste |
| "Who is the user?" | Different users, different solutions |
| "What's the success metric?" | How do we know it worked? |
| "What's the happy path?" | Optimize for the common case |
| "What happens on error?" | Users see errors, not stack traces |
| "Is this discoverable?" | Features users can't find don't exist |
| "What's the migration path?" | Existing users matter |

*Inspired by product leaders and user-centric engineering practitioners.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Engineering solution to a product problem
// "Users keep entering invalid emails"
// Bad: Add 50 validation rules
// Good: Ask why they're entering emails wrong, fix the UX

// RED FLAG: No error states designed
<Button onClick={submit}>Submit</Button>
// What happens on error? Loading? Success? Empty state?

// RED FLAG: Feature without success metric
// "Let's add dark mode"
// Why? For whom? How do we know it's working?

// RED FLAG: Power user features blocking launch
// "We need bulk actions before we can ship"
// Do we? For the first 10 users?

// RED FLAG: Ignoring existing user behavior
// Renaming things users already know
// Changing flows that work

// RED FLAG: No progressive disclosure
// Showing 50 options on first use
// Overwhelming new users to serve power users
```

### What They Approve

```typescript
// GOOD: Clear error states
{isLoading && <Spinner />}
{error && <ErrorMessage retry={refetch} />}
{isEmpty && <EmptyState action={createFirst} />}
{data && <DataView data={data} />}

// GOOD: Progressive disclosure
// New users see simple flow
// Power users can access advanced options
<Accordion title="Advanced Options" defaultOpen={false}>
  {advancedSettings}
</Accordion>

// GOOD: Success metrics defined
// Feature: One-click tipping
// Metric: Conversion rate from page view to tip
// Target: 5% of visitors complete a tip

// GOOD: Graceful migration
// Old: /user/settings
// New: /dashboard/settings
// Both work, old redirects to new with message
```

### Product Review Template

```markdown
## Product Review Checklist

**User Value:**
- [ ] Problem statement is clear
- [ ] Target user is defined
- [ ] Success metric exists

**User Experience:**
- [ ] Happy path is smooth
- [ ] Error states are designed
- [ ] Loading states exist
- [ ] Empty states guide users

**Adoption:**
- [ ] Feature is discoverable
- [ ] No breaking changes for existing users
- [ ] Migration path if needed

**Measurement:**
- [ ] Analytics events added
- [ ] Can we measure success?
- [ ] A/B test needed?
```

### Product Engineer Sayings

> "Users don't care about your architecture."

> "The best feature is the one that solves the problem."

> "Ship to learn, don't learn to ship."

> "Every feature has a cost. Not just to build—to maintain, explain, and support."

---

## Performance Engineer Perspective

Performance engineers think about speed, efficiency, and resource usage at every layer.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What's the latency?" | Users notice > 100ms |
| "Where's the hot path?" | Optimize what matters |
| "What's the memory footprint?" | Memory leaks compound |
| "Is this O(n) or O(n²)?" | Matters at scale |
| "What's cached?" | Fastest request is one not made |
| "What's the bundle size?" | Every KB is user time |
| "Is this work necessary?" | Best optimization: don't do it |

*Inspired by systems performance engineers and web performance practitioners.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Quadratic complexity hiding in plain sight
users.forEach(user => {
  const role = roles.find(r => r.userId === user.id)  // O(n*m)
})
// Better: Build a Map first, O(n+m)

// RED FLAG: Unnecessary re-renders
function Component({ data }) {
  const processed = expensiveOperation(data)  // Runs every render
  return <div>{processed}</div>
}

// RED FLAG: Unbounded data fetching
const allUsers = await db.user.findMany()  // Could be millions

// RED FLAG: Synchronous blocking operations
const data = fs.readFileSync(path)  // Blocks event loop

// RED FLAG: Bundle bloat
import _ from 'lodash'  // 70KB for one function
// Better: import debounce from 'lodash/debounce'

// RED FLAG: Memory leaks
useEffect(() => {
  const interval = setInterval(poll, 1000)
  // No cleanup! Leaks on unmount
})

// RED FLAG: Premature optimization
const memoized = useMemo(() => a + b, [a, b])  // Addition doesn't need memo
```

### What They Approve

```typescript
// GOOD: Right data structure for the job
const rolesByUserId = new Map(roles.map(r => [r.userId, r]))
users.forEach(user => {
  const role = rolesByUserId.get(user.id)  // O(1) lookup
})

// GOOD: Memoization where it matters
const processedData = useMemo(() =>
  expensiveSort(data),
  [data]  // Only recalculate when data changes
)

// GOOD: Bounded queries
const users = await db.user.findMany({
  take: 100,
  cursor: lastId ? { id: lastId } : undefined
})

// GOOD: Async operations
const data = await fs.promises.readFile(path)

// GOOD: Tree-shakeable imports
import { debounce } from 'lodash-es'

// GOOD: Cleanup effects
useEffect(() => {
  const interval = setInterval(poll, 1000)
  return () => clearInterval(interval)  // Cleanup on unmount
}, [])

// GOOD: Lazy loading
const HeavyComponent = lazy(() => import('./HeavyComponent'))
```

### Performance Review Template

```markdown
## Performance Review Checklist

**Algorithmic:**
- [ ] No hidden O(n²) or worse
- [ ] Right data structures used
- [ ] Bounded queries with pagination

**Frontend:**
- [ ] Bundle size impact measured
- [ ] Lazy loading for heavy components
- [ ] Memoization where beneficial
- [ ] No unnecessary re-renders

**Backend:**
- [ ] Async I/O used
- [ ] Database queries indexed
- [ ] N+1 queries avoided
- [ ] Response times measured

**Resources:**
- [ ] Memory leaks prevented
- [ ] Cleanup handlers in place
- [ ] Connection pooling configured
```

### Performance Engineer Sayings

> "Measure, don't guess."

> "The fastest code is code that doesn't run."

> "Premature optimization is the root of all evil—but so is premature pessimization."

> "Know your hot path. Optimize there."

---

## Data Engineer Perspective

Data engineers think about schemas, migrations, data integrity, and analytics.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What's the schema evolution plan?" | Data outlives code |
| "How do we backfill?" | New fields need old data |
| "Is this denormalized for a reason?" | Intentional vs accidental |
| "What's the source of truth?" | One authoritative source |
| "How is this audited?" | Compliance and debugging |
| "What analytics does this enable?" | Data should be queryable |
| "Is this nullable for a reason?" | Nulls complicate queries |

*Inspired by data engineering practitioners and analytics engineering community.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Nullable without reason
model User {
  email    String?  // Why optional? Every user needs email
  name     String?  // Why optional?
}

// RED FLAG: Stringly-typed data
status: String  // "active", "ACTIVE", "Active" all exist in prod

// RED FLAG: No migration strategy
// Adding required field to table with 1M rows
// ALTER TABLE users ADD COLUMN required_field NOT NULL  // Fails!

// RED FLAG: Duplicated data with no sync strategy
// User's name stored in users AND in tips
// What happens when they update their name?

// RED FLAG: No soft delete for important data
await db.user.delete({ where: { id } })  // Gone forever

// RED FLAG: Timestamps without timezone
createdAt: new Date().toISOString().split('T')[0]  // Lost timezone info

// RED FLAG: No audit trail
await db.tip.update({ data: { amount: newAmount } })  // Who changed it? When? Why?
```

### What They Approve

```typescript
// GOOD: Explicit enums
enum TipStatus {
  PENDING = 'PENDING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED'
}

// GOOD: Migration strategy
// Step 1: Add nullable column
// Step 2: Backfill data
// Step 3: Make non-nullable

// GOOD: Soft delete
model User {
  deletedAt DateTime?
  @@index([deletedAt])  // For filtering active users
}

// GOOD: Audit trail
model TipAudit {
  tipId     String
  field     String
  oldValue  String?
  newValue  String
  changedBy String
  changedAt DateTime @default(now())
}

// GOOD: Single source of truth
// Tips reference pageId, not denormalized page data
model Tip {
  pageId String
  page   Page @relation(...)
  // NOT: pageName String, pageSlug String (denormalized)
}

// GOOD: UTC timestamps
createdAt DateTime @default(now())  // Prisma handles UTC
```

### Data Review Template

```markdown
## Data Review Checklist

**Schema Design:**
- [ ] Nullability is intentional
- [ ] Enums used for fixed values
- [ ] Relationships properly defined
- [ ] Indexes on query patterns

**Migrations:**
- [ ] Migration is reversible
- [ ] Backfill strategy exists
- [ ] No breaking changes to active data

**Integrity:**
- [ ] Single source of truth identified
- [ ] Denormalization is intentional
- [ ] Audit trail for sensitive changes
- [ ] Soft delete for important data

**Analytics:**
- [ ] Data is queryable for analytics
- [ ] Timestamps are UTC
- [ ] Events are tracked for funnels
```

### Data Engineer Sayings

> "Data outlives code. Schema changes are forever."

> "If you can't query it, you don't have data—you have a write-only log."

> "Nulls are not values. They're the absence of values. Treat them differently."

> "The migration is the feature."

---

## Accessibility Engineer Perspective

Accessibility engineers ensure products work for everyone, including users with disabilities.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "Can I use this with keyboard only?" | Many users can't use mice |
| "What does the screen reader say?" | Blind users depend on this |
| "Is the contrast sufficient?" | Low vision users need contrast |
| "Are there motion alternatives?" | Vestibular disorders are real |
| "Is the focus state visible?" | Keyboard users need to see where they are |
| "Are form errors announced?" | Screen reader users need to know |
| "Is there text alternative for images?" | Not everyone can see images |

*Inspired by accessibility advocates and WCAG practitioners.*

### Red Flags They Spot Immediately

```tsx
// RED FLAG: Click handlers on divs
<div onClick={handleClick}>Click me</div>
// Not keyboard accessible, no role, no focus

// RED FLAG: Missing alt text
<img src="chart.png" />  // What does the chart show?

// RED FLAG: Color-only feedback
<span style={{ color: 'red' }}>Error</span>
// Color-blind users can't see this

// RED FLAG: Removing focus outline
button:focus { outline: none; }  // Keyboard users are now lost

// RED FLAG: Auto-playing media
<video autoPlay>  // Disorienting, wastes bandwidth

// RED FLAG: Missing form labels
<input placeholder="Email" />  // Placeholder is not a label

// RED FLAG: Unclear link text
<a href="/docs">Click here</a>  // Click where? For what?

// RED FLAG: Low contrast
color: #999 on background: #fff  // Ratio ~2.8:1, needs 4.5:1
```

### What They Approve

```tsx
// GOOD: Semantic HTML with keyboard support
<button onClick={handleClick}>Click me</button>
// Focusable, keyboard accessible, announced as button

// GOOD: Descriptive alt text
<img src="chart.png" alt="Sales increased 50% from Q1 to Q2" />

// GOOD: Multiple feedback channels
<span role="alert" style={{ color: 'red' }}>
  ⚠️ Error: Email is required
</span>
// Color + icon + text

// GOOD: Visible focus
button:focus {
  outline: 2px solid #0066cc;
  outline-offset: 2px;
}

// GOOD: Respecting motion preferences
@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; }
}

// GOOD: Proper form labels
<label htmlFor="email">Email address</label>
<input id="email" type="email" aria-describedby="email-hint" />
<span id="email-hint">We'll never share your email</span>

// GOOD: Descriptive link text
<a href="/docs">Read the documentation</a>

// GOOD: ARIA live regions for dynamic content
<div aria-live="polite" aria-atomic="true">
  {statusMessage}
</div>
```

### Accessibility Review Template

```markdown
## Accessibility Review Checklist

**Keyboard:**
- [ ] All interactive elements are focusable
- [ ] Focus order is logical
- [ ] Focus is visible
- [ ] No keyboard traps

**Screen Readers:**
- [ ] Semantic HTML used
- [ ] Images have alt text
- [ ] Form inputs have labels
- [ ] Dynamic content announced

**Visual:**
- [ ] Color contrast meets WCAG AA (4.5:1 for text)
- [ ] Color is not the only indicator
- [ ] Text can be resized to 200%
- [ ] Motion can be disabled

**Testing:**
- [ ] Tested with keyboard only
- [ ] Tested with screen reader
- [ ] Tested with browser zoom
- [ ] Automated accessibility audit passes
```

### Accessibility Engineer Sayings

> "Accessibility is not a feature. It's a requirement."

> "If you can't use it with a keyboard, you can't use it."

> "The best accessibility is invisible—it just works."

> "Accessibility benefits everyone. Curb cuts help strollers too."

---

## Mobile/Client Engineer Perspective

Mobile and client engineers think about resource constraints, offline support, and platform-specific concerns.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What's the bundle size impact?" | Every KB is download time |
| "Does this work offline?" | Networks are unreliable |
| "What about slow connections?" | Not everyone has fast internet |
| "Is this gesture accessible?" | Not all devices have gestures |
| "What's the battery impact?" | Background work drains battery |
| "Does this work on older devices?" | Not everyone has latest phone |
| "Is the touch target big enough?" | 44px minimum for touch |

*Inspired by web platform engineers and mobile performance practitioners.*

### Red Flags They Spot Immediately

```tsx
// RED FLAG: Huge bundle for small feature
import moment from 'moment'  // 300KB for date formatting
// Use Intl.DateTimeFormat or date-fns

// RED FLAG: No loading state for slow networks
function Page() {
  const { data } = useSWR('/api/data')
  return <div>{data.items.map(...)}</div>  // Crashes while loading
}

// RED FLAG: Assuming always online
const data = await fetch('/api/data')
// What happens when offline?

// RED FLAG: Tiny touch targets
<button style={{ padding: '4px' }}>×</button>
// Impossible to tap on mobile

// RED FLAG: Blocking the main thread
const sorted = hugeArray.sort((a, b) => complexComparison(a, b))
// UI freezes during sort

// RED FLAG: Excessive network requests
useEffect(() => {
  items.forEach(item => fetch(`/api/item/${item.id}`))
}, [items])  // 100 items = 100 requests

// RED FLAG: Not handling back button
// SPA doesn't restore scroll position or state on back
```

### What They Approve

```tsx
// GOOD: Minimal dependencies
const formatted = new Intl.DateTimeFormat('en', {
  dateStyle: 'medium'
}).format(date)

// GOOD: Proper loading and error states
function Page() {
  const { data, error, isLoading } = useSWR('/api/data')
  if (isLoading) return <Skeleton />
  if (error) return <ErrorState retry={mutate} />
  return <DataView data={data} />
}

// GOOD: Offline support
const { data } = useSWR('/api/data', fetcher, {
  fallbackData: localStorage.getItem('cached-data'),
  onSuccess: (data) => localStorage.setItem('cached-data', data)
})

// GOOD: Touch-friendly targets
<button style={{
  minWidth: '44px',
  minHeight: '44px',
  padding: '12px'
}}>×</button>

// GOOD: Non-blocking operations
const worker = new Worker('sort-worker.js')
worker.postMessage(hugeArray)
worker.onmessage = (e) => setData(e.data)

// GOOD: Batched requests
const data = await fetch('/api/items', {
  method: 'POST',
  body: JSON.stringify({ ids: items.map(i => i.id) })
})

// GOOD: Preserving state on navigation
// Store scroll position, form state in session storage
// Restore on back button
```

### Mobile/Client Review Template

```markdown
## Mobile/Client Review Checklist

**Bundle Size:**
- [ ] New dependencies justified
- [ ] Tree-shaking works
- [ ] Code splitting used for routes
- [ ] Lazy loading for heavy features

**Network:**
- [ ] Loading states for all async data
- [ ] Error states with retry
- [ ] Offline fallback considered
- [ ] Requests are batched where possible

**Performance:**
- [ ] No main thread blocking
- [ ] Heavy work offloaded to workers
- [ ] Animations use CSS/GPU
- [ ] Memory leaks prevented

**Mobile UX:**
- [ ] Touch targets ≥ 44px
- [ ] Works on slow connections
- [ ] Back button works correctly
- [ ] Works on older devices
```

### Mobile/Client Engineer Sayings

> "Your users are not on your MacBook Pro."

> "The network is hostile. Plan for it."

> "Every byte has a cost. Make it count."

> "Mobile-first is not mobile-only. It's constraints-first."

---

## UI/UX Designer Perspective

UI/UX Designers focus on visual coherence, design system consistency, and the feel of interactions—including AI interfaces.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "Is this using the design system?" | Consistency builds trust |
| "What's the visual hierarchy?" | Users should know where to look |
| "Does this feel responsive?" | Perceived performance matters |
| "What's the feedback for this action?" | Users need to know something happened |
| "Is the spacing consistent?" | 8px grid violations feel "off" |
| "What's the loading state?" | Blank screens feel broken |
| "Does this animation serve a purpose?" | Gratuitous animation annoys |

*Inspired by design system practitioners and developer-focused design teams.*

### Red Flags They Spot Immediately

```tsx
// RED FLAG: Inconsistent spacing
<div style={{ padding: '13px' }}>  // Not on the 4/8px grid
<div style={{ margin: '20px' }}>   // Should be 16 or 24

// RED FLAG: No loading feedback
<button onClick={async () => {
  await saveData()  // User clicks, nothing happens for 2 seconds
}}>Save</button>

// RED FLAG: Inconsistent button styles
<button className="btn-primary">Save</button>
<button style={{ background: 'blue' }}>Also Save</button>  // Different blue!

// RED FLAG: No transition on state change
{isOpen && <Modal />}  // Pops in/out jarring

// RED FLAG: Walls of text
<p>{longExplanation}</p>  // No hierarchy, no scanning

// RED FLAG: AI response with no streaming
const response = await ai.generate(prompt)  // User waits 10s, then wall of text

// RED FLAG: No skeleton/placeholder
{data ? <Content /> : null}  // Layout shifts when data loads

// RED FLAG: Misusing color
<span style={{ color: 'red' }}>Note: This is informational</span>
// Red = error. Don't use for non-errors
```

### What They Approve

```tsx
// GOOD: Design system tokens
<div className="p-4 space-y-2">  // Tailwind uses consistent scale
<Box padding={4} gap={2}>        // Or design system components

// GOOD: Loading states with feedback
<Button
  onClick={handleSave}
  loading={isSaving}
  disabled={isSaving}
>
  {isSaving ? 'Saving...' : 'Save'}
</Button>

// GOOD: Consistent components
import { Button } from '@/components/ui/button'
// One Button component, used everywhere

// GOOD: Purposeful transitions
<AnimatePresence>
  {isOpen && (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
    >
      <Modal />
    </motion.div>
  )}
</AnimatePresence>

// GOOD: Visual hierarchy
<div>
  <h2 className="text-lg font-semibold">Title</h2>
  <p className="text-sm text-muted-foreground">Supporting text</p>
</div>

// GOOD: AI streaming response
<div className="prose">
  {streamingResponse.split('').map((char, i) => (
    <span key={i} className="animate-fade-in">{char}</span>
  ))}
</div>

// GOOD: Skeleton placeholders
{isLoading ? (
  <Skeleton className="h-20 w-full" />
) : (
  <Content data={data} />
)}

// GOOD: Semantic color usage
<Alert variant="info">Note: This is informational</Alert>
<Alert variant="error">Error: Something went wrong</Alert>
```

### AI Interaction Design

```tsx
// GOOD: Streaming with typing indicator
<div className="flex gap-2">
  <Avatar src={ai} />
  <div className="flex-1">
    {isStreaming && <TypingIndicator />}
    <StreamingText content={response} />
  </div>
</div>

// GOOD: Clear AI vs human distinction
<Message
  role={message.role}
  className={cn(
    message.role === 'assistant' && 'bg-muted',
    message.role === 'user' && 'bg-primary text-primary-foreground'
  )}
/>

// GOOD: Interruptible AI responses
<Button
  variant="ghost"
  size="sm"
  onClick={stopGeneration}
  className={cn(!isGenerating && 'hidden')}
>
  Stop generating
</Button>

// GOOD: AI uncertainty indication
{confidence < 0.8 && (
  <span className="text-muted-foreground text-xs">
    I'm not fully certain about this
  </span>
)}

// GOOD: Regenerate/refine options
<div className="flex gap-2 mt-2">
  <Button variant="outline" size="sm" onClick={regenerate}>
    Try again
  </Button>
  <Button variant="outline" size="sm" onClick={refine}>
    Make it shorter
  </Button>
</div>
```

### UI/UX Review Template

```markdown
## UI/UX Review Checklist

**Visual Consistency:**
- [ ] Uses design system components
- [ ] Spacing follows grid (4px/8px)
- [ ] Colors match semantic meaning
- [ ] Typography hierarchy is clear

**Interaction Feedback:**
- [ ] Loading states for async actions
- [ ] Hover/focus states on interactive elements
- [ ] Success/error feedback after actions
- [ ] Transitions are purposeful (not gratuitous)

**Layout:**
- [ ] No layout shift on load
- [ ] Skeleton placeholders for loading
- [ ] Responsive across breakpoints
- [ ] Visual hierarchy guides the eye

**AI-Specific (if applicable):**
- [ ] Streaming responses (not blocking)
- [ ] Clear AI vs human distinction
- [ ] Interruptible generation
- [ ] Regenerate/refine options
```

### UI/UX Designer Sayings

> "If it looks off, it is off. Trust the eye."

> "Consistency is more important than perfection."

> "Loading states are not optional. Blank screens are bugs."

> "Animation should explain, not decorate."

> "AI interfaces need escape hatches. Users must feel in control."

---

## Forward Deployed/Solutions Engineer Perspective

Forward Deployed Engineers (FDEs), Solutions Engineers, and Solutions Architects work directly with customers. They see what breaks in the real world.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "Can the customer configure this themselves?" | Self-service reduces support load |
| "What happens in their edge case?" | Enterprise customers have weird setups |
| "Is this documented for non-engineers?" | Customers read docs, not code |
| "What's the migration path from competitors?" | Switching costs matter |
| "Can I demo this in 5 minutes?" | Sales cycles need quick wins |
| "What breaks when they use it wrong?" | They will use it wrong |
| "Is this feature discoverable?" | Hidden features = support tickets |

*Inspired by field engineering teams and developer experience practitioners.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Hardcoded assumptions
const MAX_USERS = 100  // Enterprise customer has 50,000 users

// RED FLAG: No configuration options
const WEBHOOK_TIMEOUT = 5000  // Customer's backend is slow, needs 30s

// RED FLAG: Undocumented error codes
throw new Error('E_INVALID_STATE')  // Customer asks "what does this mean?"

// RED FLAG: Breaking changes without migration
// v2 API removes field that customer's integration depends on

// RED FLAG: Works in demo, breaks at scale
const allRecords = await db.findMany()  // Demo: 10 records. Production: 1M records

// RED FLAG: Assumes ideal environment
if (!process.env.DATABASE_URL) throw new Error('Missing config')
// Customer: "It works locally, fails in their weird Docker setup"

// RED FLAG: No way to debug customer issues
// No customer-accessible logs, no way to trace requests
```

### What They Approve

```typescript
// GOOD: Configurable limits
const maxUsers = config.get('MAX_USERS') ?? 100
const webhookTimeout = config.get('WEBHOOK_TIMEOUT_MS') ?? 5000

// GOOD: Clear, actionable error messages
throw new ConfigError(
  'WEBHOOK_TIMEOUT_MS must be between 1000 and 60000',
  { provided: timeout, valid: '1000-60000' }
)

// GOOD: Migration guides
// CHANGELOG.md: "v2.0: `user_id` renamed to `userId`.
// Run `migrate-v2` script or add alias in config."

// GOOD: Customer-accessible debugging
app.get('/debug/health', requireApiKey, async () => ({
  database: await checkDb(),
  externalApis: await checkApis(),
  config: sanitizeConfig(config),
  version: pkg.version
}))

// GOOD: Works in weird environments
const dbUrl = process.env.DATABASE_URL
  ?? process.env.DB_CONNECTION_STRING  // Alternative name
  ?? buildFromComponents(process.env)   // Build from parts
```

### FDE Review Template

```markdown
## Forward Deployed Review Checklist

**Customer Experience:**
- [ ] Self-service configuration available
- [ ] Error messages are actionable (not just error codes)
- [ ] Documentation exists for this feature
- [ ] Works in customer's environment (not just ours)

**Integration:**
- [ ] API is consistent with existing patterns
- [ ] Breaking changes have migration path
- [ ] Webhooks/callbacks are configurable
- [ ] Authentication works with customer's IdP

**Support:**
- [ ] Customer can debug issues themselves
- [ ] Logs are accessible and meaningful
- [ ] Feature is discoverable in UI/docs
- [ ] Demo-able in sales context

**Scale:**
- [ ] Works with enterprise data volumes
- [ ] Handles customer's edge cases
- [ ] Timeout/retry behavior is configurable
```

### FDE Sayings

> "If the customer can't configure it, you'll be configuring it for them."

> "Every hardcoded value is a future support ticket."

> "The best documentation is the one the customer actually reads."

> "Demo-driven development: if you can't demo it, customers can't use it."

---

## Customer Success Engineer Perspective

Customer Success Engineers (CSEs) support customers post-sale. They see what actually breaks in production and what causes churn.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "What's the support ticket going to say?" | Anticipate the failure mode |
| "Can I explain this to a non-technical user?" | Not all customers are engineers |
| "What's the workaround?" | When things break, customers need options |
| "Is there a status page for this?" | Customers need to know if it's them or us |
| "What's the escalation path?" | Some issues need engineering |
| "Does this affect billing?" | Money issues are urgent |
| "Can they export their data?" | Customers ask this when unhappy |

*Inspired by customer success practitioners and support-first engineering teams.*

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Silent failures
await sendNotification(user)  // If this fails, customer never knows

// RED FLAG: No user-facing status
// Feature is down, but UI shows no indication

// RED FLAG: Irreversible actions without confirmation
await deleteAllUserData(userId)  // Customer: "I didn't mean to click that"

// RED FLAG: No data export
// Customer wants to leave, can't get their data out

// RED FLAG: Confusing billing implications
if (exceedsLimit) {
  chargeOverage(amount)  // Customer surprised by bill
}

// RED FLAG: No way to contact support
<ErrorBoundary fallback={<div>Something went wrong</div>} />
// No help link, no error ID, no way to report

// RED FLAG: Audit trail gaps
await updateUser(changes)  // Who changed what? When? Why?
```

### What They Approve

```typescript
// GOOD: Visible status
<StatusBanner
  status={systemStatus}
  lastUpdated={statusCheckedAt}
  statusPageUrl="/status"
/>

// GOOD: Confirmation for destructive actions
<ConfirmDialog
  title="Delete all data?"
  description="This will permanently delete 1,234 records. This cannot be undone."
  confirmLabel="Yes, delete everything"
  cancelLabel="Cancel"
/>

// GOOD: Graceful degradation with user feedback
try {
  await sendNotification(user)
} catch (e) {
  await queueForRetry(notification)
  showToast('Notification delayed, will retry automatically')
}

// GOOD: Data export
app.get('/api/export', requireAuth, async (req, res) => {
  const data = await exportUserData(req.user.id)
  res.attachment('my-data.json')
  res.json(data)
})

// GOOD: Billing transparency
if (approachingLimit) {
  showWarning(`You've used ${used}/${limit}. Overages billed at ${rate}/unit.`)
}

// GOOD: Helpful error states
<ErrorState
  title="Something went wrong"
  errorId={errorId}
  message="We've been notified and are looking into it."
  actions={[
    { label: 'Try again', onClick: retry },
    { label: 'Contact support', href: `/support?error=${errorId}` }
  ]}
/>
```

### CSE Review Template

```markdown
## Customer Success Review Checklist

**User Communication:**
- [ ] Errors are user-friendly with next steps
- [ ] Status indicators for async operations
- [ ] Email/notifications for important events
- [ ] Help links in relevant places

**Support Readiness:**
- [ ] Error IDs for tracking
- [ ] Customer-accessible logs/history
- [ ] Known issues documented
- [ ] Escalation path defined

**Trust & Safety:**
- [ ] Destructive actions have confirmation
- [ ] Billing changes are transparent
- [ ] Data export is available
- [ ] Audit trail for changes

**Resilience:**
- [ ] Graceful degradation for failures
- [ ] Retry logic for transient errors
- [ ] Workarounds documented
- [ ] Rollback plan exists
```

### CSE Sayings

> "The error message IS the documentation."

> "If support can't explain it, the feature is broken."

> "Happy path is 20% of the work. The other 80% is what happens when things go wrong."

> "Data export is an insurance policy. Customers who can leave, stay."

---

## Tech Lead Perspective

Tech leads think beyond code correctness to team velocity, maintainability, and shipping.

### Questions They Always Ask

| Question | Why It Matters |
|----------|----------------|
| "Is this the right level of abstraction?" | Over/under-abstraction both hurt |
| "Will this be obvious to someone new?" | Onboarding cost is real |
| "What's the migration path?" | Can't big-bang replace systems |
| "Does this need to exist?" | Best code is no code |
| "What's blocking shipping this today?" | Perfect is enemy of good |
| "How do we know it's working in prod?" | Observability before features |
| "What's the tech debt we're accepting?" | Make it explicit, not accidental |

### Red Flags They Spot Immediately

```typescript
// RED FLAG: Premature abstraction
class AbstractPaymentProcessorFactoryStrategy { }  // One payment provider!

// RED FLAG: Premature optimization
const memoizedResult = useMemo(() => x + 1, [x])  // Addition doesn't need memo

// RED FLAG: Cargo culting
// "We need Kubernetes" (for 100 users)
// "We need microservices" (for 3 developers)
// "We need event sourcing" (for a CRUD app)

// RED FLAG: Resume-driven development
// Using GraphQL, Kafka, and Terraform for a weekend project

// RED FLAG: Invisible tech debt
// No comment explaining why this weird thing exists
// No TODO with context for known shortcuts

// RED FLAG: Blocking on perfect
// "We can't launch until we have 100% test coverage"
// "We need to refactor this first"
```

### What They Approve

```typescript
// GOOD: Explicit tech debt
// TODO(v2): Replace with proper queue - currently in-memory, will lose jobs on restart
// Acceptable for launch, tracking in TECH_DEBT.md
const jobQueue: Job[] = []

// GOOD: Boring technology choices
// PostgreSQL instead of NewHotDB
// React instead of custom framework
// Express instead of custom server

// GOOD: Right-sized solutions
// Simple if/else instead of strategy pattern (for 2 cases)
// Direct function calls instead of event bus (for in-process)
// Monolith instead of microservices (for small team)

// GOOD: Ship then iterate
// v1: Manual process, learn what users actually need
// v2: Automate the manual process
// v3: Optimize the automation

// GOOD: Escape hatches
export function processPayment(amount: number, options?: {
  skipValidation?: boolean  // Escape hatch for edge cases
}) { }
```

### Tech Lead Review Template

```markdown
## Tech Lead Considerations

**Scope:**
- [ ] Solves the actual problem (not a related problem)
- [ ] Minimal footprint (no unnecessary changes)
- [ ] No premature optimization

**Maintainability:**
- [ ] New team member could understand this in < 30 min
- [ ] Comments explain "why" not "what"
- [ ] Consistent with existing patterns (or explicitly changing them)

**Shipping:**
- [ ] Can be feature-flagged if needed
- [ ] Rollback plan exists
- [ ] Tech debt documented if accepted

**Team Impact:**
- [ ] Doesn't block other work
- [ ] Doesn't require everyone to learn new tool/pattern
- [ ] Reviewed by someone who will maintain it
```

### The "Launch vs Perfect" Decision Framework

```
                    ┌─────────────────────────────────────┐
                    │     Is this blocking launch?        │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
                   Yes            Maybe               No
                    │                 │                 │
                    ▼                 ▼                 ▼
              Fix it now    Can we ship with      Add to backlog
                            a workaround?         (with context)
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
                   Yes               No               N/A
                    │                 │
                    ▼                 ▼
              Ship with          Fix it now
              workaround,
              document debt
```

### Tech Lead Sayings

> "Good enough today beats perfect never."

> "We can always make it better. We can't always make it exist."

> "The goal is learning, not correctness. Ship, measure, iterate."

> "Three similar lines are better than one clever abstraction."

> "If it takes more time to automate than to just do it 10 times, don't automate it yet."

> "Your job is to ship, not to write code. Code is a means, not an end."

---

## Software Philosophy Perspectives

Different schools of thought in software engineering. Useful for understanding trade-offs and why smart people disagree.

**Prompts:** See `PROMPTS.md` → "Engineering Persona Prompts" for AI-powered code reviews and design decisions using these perspectives.

### Pragmatists vs Purists

When you encounter conflicting advice, it often comes from these two camps:

#### The Pragmatist Camp

*Inspired by shipping-focused engineering leaders and framework authors.*

**Core Beliefs:**
- "Dead code is tech debt. If you're not using it, delete it. YAGNI."
- "Don't fight the framework. Embrace the patterns it provides."
- "The best code is code that ships."
- "Perfect is the enemy of good."

**On Error Handling:**
> "tRPC already handles errors beautifully. Don't fight the framework. If you want Result types, use a language that has them natively (Rust, OCaml). In TypeScript, embrace try/catch."

**On Abstractions:**
> "Three similar lines are better than one clever abstraction."

**When They're Right:**
- Shipping under time pressure
- Small teams where simplicity matters
- Prototyping/exploring problem space
- When the "right" solution has unclear ROI

#### The Purist/Craft Camp

*Inspired by language designers, software craftsmen, and Domain-Driven Design practitioners.*

**Core Beliefs:**
- "Simple is not the same as easy."
- "Design for change, not for performance."
- "Make illegal states unrepresentable."
- "Code is read 10x more than written."

**On Error Handling:**
> "Business logic shouldn't know about HTTP codes or tRPC. Your `core` package should be framework-agnostic. Result types let you express domain errors like `INSUFFICIENT_BALANCE` or `PAGE_INACTIVE` without coupling to transport layer errors."

**On Abstractions:**
> "Abstractions should hide complexity, not just lines of code."

**When They're Right:**
- Long-lived codebases
- Large teams where consistency matters
- Domain complexity that needs to be modeled
- When refactoring costs are high

### Functional Programming Advocates

*Inspired by functional programming communities and type-safe language practitioners.*

**Core Beliefs:**
- "Exceptions are side effects that break referential transparency."
- "Result types make errors explicit in the type signature - you can't forget to handle them."
- "Immutability prevents entire classes of bugs."
- "Parse, don't validate."

**On TypeScript Specifically:**
> "TypeScript's type system is powerful enough to enforce many invariants at compile time. Use it. `Result<T, E>` is more informative than `throws unknown`."

**When They're Right:**
- Error handling is critical (payments, auth)
- Complex state transformations
- Need for predictable, testable code
- Building libraries consumed by others

### Testing-Focused Engineers

*Inspired by TDD practitioners and testing library authors.*

**Core Beliefs:**
- "If it's hard to test, the design is wrong."
- "Test behavior, not implementation."
- "Pure functions that return Results are trivial to test. No mocking, no try/catch in tests."
- "Integration tests > unit tests for most apps."

**On Result Types:**
> "Pure functions that return Results are trivial to test. No mocking, no try/catch in tests. Just `expect(result.ok).toBe(false)`."

**When They're Right:**
- Building confidence in critical paths
- Refactoring existing code safely
- Onboarding new team members
- Code that must not regress

### The Synthesis

Most production codebases benefit from a blend:

| Context | Lean Toward |
|---------|-------------|
| Startup MVP | Pragmatist |
| Fintech/Healthcare | Purist |
| CRUD app | Pragmatist |
| Complex domain logic | Purist/DDD |
| Framework-specific code (routes, UI) | Pragmatist |
| Core business logic | Purist |
| Prototype | Pragmatist |
| Library for others | Purist/FP |

### Decision Framework

When facing a design choice:

```
1. What would the pragmatist say?
   → "Just ship it, refactor later"

2. What would the purist say?
   → "Design it right, it'll pay off"

3. What's the actual context?
   → Team size, timeline, domain complexity, expected lifespan

4. What's the reversibility?
   → Easy to change later? → Pragmatist
   → Hard to change later? → Purist
```

---

## Code Quality (Any Senior Engineer)

### Universal Red Flags

```typescript
// RED FLAG: Magic numbers
if (status === 3) { ... }  // What is 3?

// RED FLAG: Duplicated logic
// Same regex in 3 files, same validation in 5 places

// RED FLAG: Catch-all error handling
try { ... } catch (e) { console.log(e) }  // Swallowed!

// RED FLAG: Comments explaining "what" not "why"
// Increment counter by 1
counter += 1

// RED FLAG: Boolean parameters
processUser(user, true, false, true)  // What do these mean?

// RED FLAG: Premature abstraction
// AbstractFactoryStrategyProvider for one use case
```

### Universal Approvals

```typescript
// GOOD: Named constants
const TIP_STATUS = { PENDING: 1, COMPLETED: 2, FAILED: 3 } as const
if (status === TIP_STATUS.COMPLETED) { ... }

// GOOD: Single source of truth
// One validation function, imported everywhere

// GOOD: Error boundaries with context
try { ... } catch (e) {
  logger.error('Failed to process payment', { userId, amount, error: e })
  throw new PaymentError('Processing failed', { cause: e })
}

// GOOD: Comments explaining "why"
// Lowercase addresses to prevent case-sensitive index misses
// (Ethereum addresses are case-insensitive but checksummed)
const normalized = address.toLowerCase()

// GOOD: Options objects over boolean params
processUser(user, { sendEmail: true, validate: false, async: true })
```

---

## Domain-Specific Review Template

Use this template to document domain-specific patterns for your project. Fill in the blanks for your critical paths.

### [Critical Domain] Handling (Current State)

| Aspect | Status | Senior Feedback |
|--------|--------|-----------------|
| Format validation | ⬜ | "Is the format correct? What library validates it?" |
| Normalization | ⬜ | "Is data stored consistently?" |
| Single source | ⬜ | "Is validation logic in one place?" |
| Required fields | ⬜ | "Should this be optional or required?" |
| Integration tests | ⬜ | "Are there tests against real systems?" |

### Example: Ethereum Address Handling

For crypto/Web3 projects, address handling is critical:

```typescript
// Recommended pattern: Single validation function
import { isAddress, getAddress } from 'viem'

/**
 * Validate and normalize an Ethereum address.
 * - Validates format AND checksum (EIP-55)
 * - Returns lowercase for consistent storage
 * - Throws with context on invalid input
 */
export function validateAndNormalizeAddress(
  address: string,
  context: string
): `0x${string}` {
  if (!address || typeof address !== 'string') {
    throw new AddressValidationError(`Missing address in ${context}`)
  }

  if (!isAddress(address)) {
    throw new AddressValidationError(
      `Invalid address format in ${context}: ${address}`
    )
  }

  // getAddress returns checksummed, we lowercase for storage
  return getAddress(address).toLowerCase() as `0x${string}`
}
```

Key principles:
- **Validate at boundaries** - Check input when it enters the system
- **Normalize early** - Convert to canonical form (e.g., lowercase) before storage
- **Single source of truth** - One validation function, used everywhere
- **Fail fast with context** - Clear error messages including where validation failed

---

## Pre-Ship Checklist

Before shipping any feature, ask:

### Security
- [ ] What's the worst case if this is exploited?
- [ ] Where does untrusted input enter?
- [ ] Is authentication and authorization correct?
- [ ] Are secrets/PII protected in logs?

### Reliability
- [ ] What happens if this fails?
- [ ] Is it idempotent?
- [ ] Is there a rollback plan?

### Maintainability
- [ ] Is there a single source of truth?
- [ ] Are the tests meaningful?
- [ ] Will I understand this in 6 months?

### Performance
- [ ] What happens at 10x load?
- [ ] Are queries indexed?
- [ ] Is there unnecessary work?

---

## Quotes to Remember

> "If it's critical, it needs defense in depth. One check is a bug waiting to happen."
> — Security Engineers

> "Same inputs must produce same outputs. If they don't, you have a bug."
> — Blockchain Engineers

> "The best code is code that doesn't exist. The second best is code that's boring."
> — Backend Engineers

> "Code is read 10x more than written. Optimize for the reader."
> — Everyone

---

*Last updated: December 9, 2025*
