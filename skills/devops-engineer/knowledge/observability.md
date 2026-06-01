---
name: Observability
description: Logging, metrics, tracing, alerting patterns
triggers: [logging, monitoring, metrics, tracing, observability]
type: pattern
---

# Observability Principles

Logs, metrics, traces, and alerting patterns.

---

## The Triad

```
Logs:    What happened (events, errors)
Metrics: How much (counters, gauges, histograms)
Traces:  Where (request flow across services)
```

---

## Minimum Viable Observability

```
├── Structured logs (JSON, not strings)
├── Error tracking (Sentry)
├── Basic metrics (response times, error rates)
├── Health check endpoint
└── Alerts on SLOs
```

---

## Structured Logging

```typescript
// String concatenation (hard to parse)
console.log(`Created tip ${tipId} for page ${pageId}`);

// Structured (queryable, machine-readable)
log.info("Tip created", {
  tipId,
  pageId,
  amountCents,
  timestamp: new Date().toISOString(),
});
```

---

## Log Levels

```
ERROR   → Something broke, needs attention
WARN    → Something unexpected, may need attention
INFO    → Normal operation, useful for debugging
DEBUG   → Detailed info, usually disabled in prod
```

---

## Health Checks

Every service needs health endpoints:

```typescript
// Simple health check
GET /health
{ status: "ok" }

// Detailed health check
GET /health/ready
{
  status: "ok",
  checks: {
    database: "ok",
    redis: "ok",
    externalApi: "degraded"
  }
}
```

---

## Metrics to Track

```
├── Request rate (requests/second)
├── Error rate (errors/requests)
├── Latency (p50, p95, p99)
├── Saturation (CPU, memory, connections)
└── Business metrics (signups, purchases)
```

---

## Alerting

```
Alert on SLOs, not symptoms:
├── CPU > 80% (less useful)
├── Error rate > 1% for 5 minutes (actionable)
├── p99 latency > 500ms for 10 minutes (actionable)

Runnable alerts include:
├── What's broken?
├── How to verify?
├── How to fix?
├── Who to escalate to?
```

---

## Correlation IDs

Trace requests across services:

```typescript
// Generate at edge
const correlationId = req.headers['x-correlation-id'] || uuid();

// Pass to all downstream calls
await fetch(url, {
  headers: { 'x-correlation-id': correlationId }
});

// Include in all logs
log.info("Processing request", { correlationId, ... });
```

---

## Observability Budget

Plan observability for each feature:

```
├── What metrics will you track?
├── What alerts will fire?
├── How will you debug in production?
```

---

*Template. Adapt to your needs.*
