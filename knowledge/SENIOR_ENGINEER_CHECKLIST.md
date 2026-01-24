# Senior Engineer Checklist

## How to Use This Document

Before shipping any feature touching critical paths (money, auth, data):

1. Pick the relevant domain sections below
2. Ask yourself each question
3. If you can't answer confidently, that's a gap to address
4. Document your answers in PR descriptions

---

## Personas Summary

| Persona | Focus | Key Question |
|---------|-------|--------------|
| **Security Engineer** | Threats, input validation | "What's the threat model?" |
| **Web3/Blockchain** | Addresses, determinism, gas | "Is this address checksummed?" |
| **Backend/Systems** | Scale, idempotency | "What happens at 10x load?" |
| **DevOps/SRE** | Observability, runbooks | "How do we know it's working?" |
| **Product Engineer** | User value, metrics | "What problem does this solve?" |
| **Performance Engineer** | Latency, complexity | "What's the hot path?" |
| **Data Engineer** | Schema, migrations | "What's the source of truth?" |
| **Accessibility** | Keyboard, screen readers | "Can I use this with keyboard only?" |
| **Mobile/Client** | Bundle size, offline | "Does this work offline?" |
| **UI/UX Designer** | Design system, feedback | "Is this using the design system?" |
| **FDE/Solutions** | Customer config | "Can the customer configure this?" |
| **Customer Success** | Support readiness | "What's the support ticket going to say?" |
| **Tech Lead** | Shipping, trade-offs | "Is this the right level of abstraction?" |

---

## Security Engineer

### Key Questions
- What's the threat model?
- What if this input is malicious?
- Who can access this? Who shouldn't?
- What's logged? What shouldn't be?
- What secrets are involved?

### Red Flags
- Raw user input in queries
- Missing auth checks
- Secrets in code/logs
- Over-permissive access

### Approval Criteria
- [ ] Threat model documented
- [ ] Input validated at boundaries
- [ ] Auth/authz verified
- [ ] No secrets exposed
- [ ] Audit logging present

---

## Web3/Blockchain Engineer

### Key Questions
- Is the address checksummed?
- What if this transaction reverts?
- What's the gas cost at scale?
- Is there reentrancy risk?
- What's the MEV exposure?

### Red Flags
- Unchecked external calls
- State changes after external calls
- Missing reentrancy guards on value transfer
- Hardcoded gas limits
- Flash loan vulnerability

### Approval Criteria
- [ ] CEI pattern followed (Checks-Effects-Interactions)
- [ ] Reentrancy guards where needed
- [ ] Gas estimates documented
- [ ] Testnet deployment verified
- [ ] Slither clean (or findings documented)

---

## Backend/Systems Engineer

### Key Questions
- What happens at 10x load?
- Is this idempotent?
- What's the failure mode?
- Where's the bottleneck?
- How do we debug in production?

### Red Flags
- N+1 queries
- Missing indexes
- No retry logic on network calls
- Unbounded data fetching
- Missing timeouts

### Approval Criteria
- [ ] Idempotent where expected
- [ ] Timeouts on all external calls
- [ ] Graceful degradation
- [ ] Structured logging
- [ ] Load tested (if critical path)

---

## Product Engineer

### Key Questions
- What problem does this solve?
- How do we know it's working?
- What's the user journey?
- What's the fallback experience?
- Who's the first user?

### Red Flags
- Feature without clear problem
- No success metrics defined
- No error states designed
- Missing loading states
- No feedback on actions

### Approval Criteria
- [ ] User problem clearly stated
- [ ] Success metrics defined
- [ ] Error states handled
- [ ] Loading/empty states present
- [ ] User feedback on actions

---

## Pragmatist vs Purist

### When to be Pragmatic
- Shipping deadline
- Throwaway prototype
- Reversible decisions
- Proof of concept
- One-time scripts

### When to be a Purist
- Security-critical code
- Core domain logic
- Public APIs
- Database schemas
- Money movement

### The Test
```
"If this is wrong, how bad is it?"

Reversible + low impact → be pragmatic
Irreversible + high impact → be a purist
```

---

## Pre-Ship Checklist by Domain

### Any Feature
- [ ] Tests exist and pass
- [ ] Error handling present
- [ ] Logging appropriate
- [ ] Documentation updated
- [ ] Reviewed by someone else

### Money/Payment Features
- [ ] Security review completed
- [ ] Idempotency verified
- [ ] Audit logging present
- [ ] Reconciliation possible
- [ ] Manual intervention path exists

### User-Facing Features
- [ ] Loading states present
- [ ] Error states present
- [ ] Empty states present
- [ ] Accessibility checked
- [ ] Mobile responsive

### Data/Schema Changes
- [ ] Migration reversible
- [ ] Backward compatible
- [ ] Data validated
- [ ] Indexes added
- [ ] Backup strategy documented
