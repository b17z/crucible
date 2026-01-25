# Senior Smart Contract Engineer Checklist

*The personas that review your Solidity before it holds real money.*

---

## The Personas

| Persona | Focus | Nightmare Scenario |
|---------|-------|-------------------|
| **Security Auditor** | Finding exploits | Your contract gets drained |
| **Gas Optimizer** | Efficiency | Users pay $50 for a $10 transaction |
| **Protocol Architect** | System design | Upgrade breaks everything |
| **MEV Researcher** | Economic attacks | Bots front-run every tx |
| **Formal Verification Eng** | Mathematical proofs | "But the invariant said..." |
| **Incident Responder** | What happens when it breaks | No pause, no recovery |

---

## Security Auditor

*Inspired by industry security researchers and audit firms.*

*"I get paid to break things. Let me break yours."*

### First Pass Questions

```
[ ] Can I drain the contract?
[ ] Can I brick the contract?
[ ] Can I grief other users?
[ ] Can I extract value I shouldn't have?
[ ] What's the worst thing an admin can do?
[ ] What's the worst thing a user can do?
[ ] What's the worst thing another contract can do?
```

### The Checklist

**Access Control:**
```
[ ] Who can call each function?
[ ] Are there admin functions? What can they do?
[ ] Can admin rug users? (Spoiler: if yes, they will be accused)
[ ] Is there a timelock on admin actions?
[ ] What happens if admin key is compromised?
```

**Reentrancy:**
```
[ ] Any external calls? (call, transfer, send, safeTransfer)
[ ] Is state updated BEFORE external calls? (CEI pattern)
[ ] Is ReentrancyGuard used on sensitive functions?
[ ] Can a callback re-enter ANY function, not just this one?
[ ] Read-only reentrancy? (view functions during callback)
```

**Integer Handling:**
```
[ ] Using Solidity 0.8.x? (built-in overflow checks)
[ ] Any `unchecked` blocks? Are they safe?
[ ] Division before multiplication? (precision loss)
[ ] Rounding direction: in favor of protocol or user?
```

**External Interactions:**
```
[ ] What if the external call fails?
[ ] What if the external call returns unexpected data?
[ ] What if the token is fee-on-transfer?
[ ] What if the token is rebasing?
[ ] What if the token is ERC777 (callbacks)?
[ ] What if the token blacklists this contract?
```

**State Machine:**
```
[ ] Can I reach an invalid state?
[ ] Can I skip states?
[ ] Can I go backwards in states?
[ ] What happens if I call functions in unexpected order?
```

### Red Flags I Look For

```solidity
// ❌ External call before state update
token.transfer(user, amount);
balances[user] = 0;  // TOO LATE

// ❌ Unchecked return value
token.transfer(user, amount);  // What if it returns false?

// ❌ tx.origin for auth
require(tx.origin == owner);  // Phishable

// ❌ Floating pragma
pragma solidity ^0.8.0;  // Which 0.8.x? They have different bugs.

// ❌ Hardcoded addresses
address constant USDC = 0xA0b8...;  // What about other chains?

// ❌ Block.timestamp for randomness
uint256 random = block.timestamp % 100;  // Miners can manipulate
```

### What I Approve

```solidity
// ✅ CEI Pattern
uint256 amount = balances[msg.sender];  // Check
balances[msg.sender] = 0;               // Effect
token.safeTransfer(msg.sender, amount); // Interaction

// ✅ Explicit state transitions
require(status == Status.Open, "Wrong status");
status = Status.Settling;

// ✅ SafeERC20 for all token operations
using SafeERC20 for IERC20;
token.safeTransfer(to, amount);

// ✅ Locked pragma
pragma solidity 0.8.19;

// ✅ Immutable for things that don't change
address public immutable token;
```

---

## Gas Optimizer

*Inspired by DeFi protocol teams and MEV researchers.*

*"Every opcode costs money. Let's count them."*

### First Pass Questions

```
[ ] What are the hot paths? (frequent operations)
[ ] What are the cold paths? (rare operations)
[ ] How much does the average user pay?
[ ] How much does the worst case cost?
[ ] Are there any unbounded loops?
```

### The Checklist

**Storage:**
```
[ ] Using storage when memory would work?
[ ] Reading same storage slot multiple times? (cache it)
[ ] Can variables be packed? (multiple uint8s in one slot)
[ ] Using mappings instead of arrays where possible?
[ ] Deleting storage to get gas refunds?
```

**Loops:**
```
[ ] Any unbounded loops? (DoS vector)
[ ] Caching array length?
[ ] Using unchecked for loop counters?
[ ] ++i instead of i++?
```

**Function Calls:**
```
[ ] External vs public vs internal vs private?
[ ] Can this be a view/pure function?
[ ] Are we paying for unused return values?
```

**Data Location:**
```
[ ] calldata vs memory for function params?
[ ] storage vs memory for local variables?
```

### Gas Optimization Patterns

```solidity
// ❌ Expensive
function sum(uint256[] memory values) public pure returns (uint256) {
    uint256 total = 0;
    for (uint256 i = 0; i < values.length; i++) {
        total += values[i];
    }
    return total;
}

// ✅ Cheaper (~40% less gas)
function sum(uint256[] calldata values) public pure returns (uint256 total) {
    uint256 len = values.length;
    for (uint256 i; i < len; ) {
        total += values[i];
        unchecked { ++i; }
    }
}
```

### When NOT to Optimize

```
// Settlement happens once per contract
// Users pay ~$0.05 on Base
// Don't sacrifice clarity for $0.01 savings

function executeSettlement() external onlySettling nonReentrant {
    // Clear code > slightly cheaper code
    // This function runs once. Optimize clarity.
}
```

---

## Protocol Architect

*Inspired by teams building foundational DeFi protocols.*

*"How does this fit into the broader system?"*

### First Pass Questions

```
[ ] What's the trust model?
[ ] Who can do what?
[ ] What happens if a dependency fails?
[ ] How do we upgrade without rugging users?
[ ] What are the economic assumptions?
```

### The Checklist

**System Boundaries:**
```
[ ] What's on-chain vs off-chain?
[ ] What's the source of truth?
[ ] What are the external dependencies?
[ ] What if an oracle fails?
[ ] What if a bridge fails?
```

**Upgrade Path:**
```
[ ] Is the contract upgradeable?
[ ] If yes: Who controls upgrades? Timelock?
[ ] If no: How do we migrate if needed?
[ ] Can users exit before an upgrade?
```

**Composability:**
```
[ ] Can other contracts integrate with this?
[ ] What if someone builds on top of us?
[ ] Are we making assumptions about callers?
```

### Design Patterns I Recommend

```
1. IMMUTABLE BY DEFAULT
   - Deploy new version, migrate users
   - Users can verify code won't change
   - No admin rug risk

2. IF UPGRADEABLE, TIMELOCK + MULTISIG
   - 48h timelock minimum
   - Users can exit if they don't like upgrade
   - Multiple signers required

3. ESCAPE HATCHES
   - Users can always withdraw their funds
   - No function can permanently lock user funds
   - Emergency pause is time-limited
```

---

## MEV Researcher

*Inspired by MEV research teams and searchers.*

*"I make money from your users' transactions. Let me show you how."*

### First Pass Questions

```
[ ] Can I front-run this?
[ ] Can I sandwich attack this?
[ ] Can I back-run this?
[ ] Is there extractable value?
[ ] What's the worst MEV scenario?
```

### The Checklist

**Front-Running:**
```
[ ] Does transaction order matter?
[ ] Can someone see pending txs and profit?
[ ] Price-sensitive operations: slippage protection?
[ ] Commit-reveal needed?
```

**For Escrow/Settlement Contracts:**
```
[ ] Can someone see settlement amounts and front-run?
   → Usually no, amounts are submitted by creator, not price-sensitive
[ ] Can someone sandwich a deposit?
   → Usually no, it's just token transfer, no price impact
[ ] Can someone extract value from settlement?
   → Usually no, fixed amounts, no market interaction
```

### MEV-Safe Patterns

```solidity
// ❌ MEV-vulnerable (DEX swap)
function swap(uint256 amountIn) external {
    uint256 amountOut = getPrice() * amountIn;
    // Attacker sees this, front-runs, moves price
}

// ✅ MEV-protected
function swap(uint256 amountIn, uint256 minAmountOut) external {
    uint256 amountOut = getPrice() * amountIn;
    require(amountOut >= minAmountOut, "Slippage");
    // User sets acceptable slippage
}
```

---

## Formal Verification Engineer

*Inspired by formal methods teams and verification tool builders.*

*"Can you prove it's correct?"*

### First Pass Questions

```
[ ] What are the invariants?
[ ] Can we state them formally?
[ ] What properties must always hold?
[ ] What's the state space?
```

### The Checklist

**Invariants (must ALWAYS be true):**
```
[ ] Conservation: Funds in == Funds out
[ ] No negative balances
[ ] No overflow (less relevant with 0.8.x)
[ ] Access control: Only authorized can do X
[ ] State transitions: Only valid paths
```

### Example Invariants

```solidity
// 1. CONSERVATION
// The contract balance equals sum of all commitments minus withdrawals
invariant conservation:
    token.balanceOf(address(this)) ==
    sum(participants[p].commitment for all p where !hasWithdrawn)

// 2. NO OVER-WITHDRAWAL
// Nobody can owe more than they committed
invariant noOverWithdrawal:
    forall p: participants[p].owes <= participants[p].commitment

// 3. SETTLEMENT VALIDITY
// Total owed cannot exceed total committed
invariant settlementValidity:
    totalOwed <= totalCommitted

// 4. STATUS MONOTONICITY
// Status can only move forward (Open → Settling → Closed)
invariant statusMonotonicity:
    old(status) == Settling implies status != Open
```

### Tools

- **Formal verification provers** — Mathematical proof of correctness
- **Echidna** — Fuzzer that finds invariant violations
- **Foundry Invariant Tests** — Property-based testing in Solidity

---

## Incident Responder

*Inspired by white hat security teams and incident response practitioners.*

*"Okay it's broken. Now what?"*

### First Pass Questions

```
[ ] Is there a pause function?
[ ] Who can pause?
[ ] What happens when paused?
[ ] Can users still withdraw when paused?
[ ] Is there a time limit on pause?
```

### The Checklist

**Emergency Controls:**
```
[ ] Pause mechanism exists?
[ ] Pause is time-limited? (can't pause forever)
[ ] Users can exit when paused?
[ ] Events emitted for all admin actions?
[ ] Contact info for security reports?
```

**Recovery:**
```
[ ] Can we upgrade if there's a bug?
[ ] If no upgrades, what's the migration plan?
[ ] Is there a bug bounty?
[ ] Is there incident response documentation?
```

### Design Patterns

```solidity
// ✅ Pausable with time limit
uint256 public pauseDeadline;

function pause() external onlyAdmin {
    require(pauseDeadline == 0, "Already paused");
    pauseDeadline = block.timestamp + 7 days;  // Auto-unpause after 7 days
    emit Paused(msg.sender);
}

function unpause() external {
    require(block.timestamp >= pauseDeadline, "Not expired");
    pauseDeadline = 0;
    emit Unpaused();
}

// ✅ Emergency withdrawal always available
function emergencyWithdraw() external {
    // Even when paused, users can exit
    // Might forfeit rewards, but funds are safe
}
```

---

## The Meta-Checklist

Before deploying ANY contract:

```
[ ] Security Auditor: Can anyone drain/brick this?
[ ] Gas Optimizer: Is the hot path affordable?
[ ] Protocol Architect: What's the failure mode?
[ ] MEV Researcher: Can bots extract value?
[ ] Formal Verification: What invariants must hold?
[ ] Incident Responder: What happens when it breaks?
```

If you can answer all of these, ship it.

---

## Quotes to Remember

> "The best smart contract is one you don't need to write."

> "Every line of code is a liability."

> "Complexity is the enemy of security."

> "The Ethereum staking contract holds $30B because it's 200 lines of boring code."

> "If you need a timelock to protect users from yourself, maybe don't have that power."

---

## References

- Smart Contract Principles: `SMART_CONTRACT_PRINCIPLES.md`
- Vulnerability Catalog: `SC_VULNERABILITY_CATALOG.md`
- Security Libraries: `SC_OPENZEPPELIN.md`
- Slither Reference: `SC_SLITHER_REFERENCE.md`
- Security Tooling: `SC_TOOLING.md`
