---
name: Smart Contract Principles
description: EVM patterns - reentrancy, CEI, gas optimization, upgrade safety
triggers: [solidity, smart-contract, web3, evm, ethereum, blockchain]
type: principle
assertions: smart-contract.yaml
---

# Smart Contract Principles

---

## The EVM Cost Model

```
TRADITIONAL BACKEND:         SMART CONTRACTS:
├── State is cheap            State costs ~20k gas/32 bytes
├── Computation is cheap      Computation costs gas
├── Side effects are "free"   Side effects cost gas + risk
├── Bugs are fixable          Deployed code is immutable
└── Complexity is manageable  Complexity increases attack surface
```

---

## Review Checklist

```
[ ] CEI pattern followed (Checks-Effects-Interactions)
[ ] Reentrancy guards on external call + value functions
[ ] No tx.origin for authentication
[ ] Address zero checks on critical params
[ ] Slither clean (or findings documented)
[ ] Access control on privileged functions
[ ] Events emitted for state changes
[ ] No hardcoded addresses (use immutable/constructor)
```

---

## CEI Pattern

Checks-Effects-Interactions:

```solidity
// Safe: CEI pattern
function withdraw() external {
    uint256 amount = balances[msg.sender];  // CHECK
    balances[msg.sender] = 0;               // EFFECT (state first)
    (bool success, ) = msg.sender.call{value: amount}("");  // INTERACTION
    require(success, "Transfer failed");
}

// Unsafe: Interaction before effect = reentrancy
function withdraw() external {
    uint256 amount = balances[msg.sender];
    (bool success, ) = msg.sender.call{value: amount}("");  // INTERACTION
    balances[msg.sender] = 0;  // EFFECT after = vulnerable
}
```

---

## State Optimization

```solidity
// Constant: Compile-time, zero gas to read
uint256 public constant MAX_FEE = 1000;

// Immutable: Set once in constructor, cheaper reads
address public immutable owner;

// Storage: 20,000 gas to set, 2,100 gas to read
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
// Vulnerable to phishing
require(tx.origin == owner);

// Use msg.sender
require(msg.sender == owner);
```

### Unchecked Returns
```solidity
// Ignoring return value
token.transfer(to, amount);

// Using SafeERC20
using SafeERC20 for IERC20;
token.safeTransfer(to, amount);
```

---

## Security Invariants

Properties that must hold:

```
1. Conservation: sum(balances) == totalSupply
2. No over-withdrawal: user.withdrawn <= user.entitled
3. Monotonicity: Open → Settling → Closed (state transitions)
4. Access: only owner can call admin functions
```

Test invariants with fuzzing (Foundry, Echidna).

---

## Gas Optimization

Cache values in hot paths:

```solidity
// Cache array length
uint256 len = values.length;
for (uint256 i; i < len; ) {
    total += values[i];
    unchecked { ++i; }  // Safe when i < len
}
```

Prioritize clarity for infrequent operations.

---

## Anti-Patterns

```
- Premature upgradeability (adds complexity, admin risk)
- Deep inheritance (hard to audit)
- God contracts (too much in one place)
- Magic numbers (use constants)
```

---

*Template. Adapt to your needs.*
