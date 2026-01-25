# Smart Contract Principles

Bugs are permanent. Design accordingly.

---

## The EVM Cost Model

```
TRADITIONAL BACKEND:         SMART CONTRACTS:
├── State is cheap            State is EXPENSIVE (~20k gas/32 bytes)
├── Computation is cheap      Computation is EXPENSIVE
├── Side effects are "free"   Side effects are EXPENSIVE + RISKY
├── Bugs are fixable          Bugs are PERMANENT
└── Complexity is manageable  Complexity KILLS
```

---

## Quick Checklist

```
☐ CEI pattern followed (Checks-Effects-Interactions)
☐ Reentrancy guards on external call + value functions
☐ No tx.origin for authentication
☐ Address zero checks on critical params
☐ Slither clean (or findings documented)
☐ Access control on privileged functions
☐ Events emitted for state changes
☐ No hardcoded addresses (use immutable/constructor)
```

---

## CEI Pattern

**Checks-Effects-Interactions** — the most important pattern:

```solidity
// ✅ Safe: CEI pattern
function withdraw() external {
    uint256 amount = balances[msg.sender];  // CHECK
    balances[msg.sender] = 0;               // EFFECT (state first!)
    (bool success, ) = msg.sender.call{value: amount}("");  // INTERACTION
    require(success, "Transfer failed");
}

// ❌ Unsafe: Interaction before effect = reentrancy
function withdraw() external {
    uint256 amount = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: amount}("");  // INTERACTION
    balances[msg.sender] = 0;  // EFFECT after = vulnerable!
}
```

---

## State Optimization

```solidity
// ✅ Constant: Compile-time, zero gas to read
uint256 public constant MAX_FEE = 1000;

// ✅ Immutable: Set once in constructor, cheaper reads
address public immutable owner;

// ⚠️ Storage: 20,000 gas to set, 2,100 gas to read
uint256 public mutableValue;
```

---

## Common Vulnerabilities

### Reentrancy
```solidity
// Use ReentrancyGuard
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

function withdraw() external nonReentrant { ... }
```

### tx.origin
```solidity
// ❌ Vulnerable to phishing
require(tx.origin == owner);

// ✅ Use msg.sender
require(msg.sender == owner);
```

### Unchecked Returns
```solidity
// ❌ Ignoring return value
token.transfer(to, amount);

// ✅ Using SafeERC20
using SafeERC20 for IERC20;
token.safeTransfer(to, amount);
```

---

## Security Invariants

Properties that must always hold:

```
1. Conservation: sum(balances) == totalSupply
2. No over-withdrawal: user.withdrawn <= user.entitled
3. Monotonicity: Open → Settling → Closed (never backwards)
4. Access: only owner can call admin functions
```

Test with fuzzing (Foundry, Echidna).

---

## Gas Optimization

Only optimize hot paths:

```solidity
// Cache array length
uint256 len = values.length;
for (uint256 i; i < len; ) {
    total += values[i];
    unchecked { ++i; }  // Safe when i < len
}
```

**Clarity wins for infrequent operations.**

---

## Anti-Patterns

```
❌ Premature upgradeability (adds complexity, admin risk)
❌ Deep inheritance (hard to audit)
❌ God contracts (too much in one place)
❌ Magic numbers (use constants)
```

---

## Simplicity Wins

The Ethereum 2.0 Deposit Contract:
- ~200 lines
- $30+ billion
- No admin keys
- Never been hacked

```
Security ≈ 1 / Complexity
```

---

*Template. Customize for your protocol.*
