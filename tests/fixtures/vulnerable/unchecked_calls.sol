// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

// BAD: Unchecked return values and dangerous patterns
contract UnsafeToken {
    IERC20 public token;
    address public owner;

    constructor(address _token) {
        token = IERC20(_token);
        owner = msg.sender;
    }

    // BAD: Unchecked transfer return value
    function withdrawTokens(address to, uint256 amount) external {
        // This can silently fail!
        token.transfer(to, amount);
    }

    // BAD: Unchecked transferFrom
    function depositTokens(uint256 amount) external {
        token.transferFrom(msg.sender, address(this), amount);
    }

    // BAD: No zero address check + tx.origin auth (phishing vulnerability)
    function setOwner(address newOwner) external {
        require(tx.origin == owner, "Not owner");  // BAD: tx.origin for auth
        // Missing: require(newOwner != address(0))
        owner = newOwner;
    }

    // BAD: Delegatecall to user-supplied address
    function execute(address target, bytes calldata data) external {
        require(msg.sender == owner, "Not owner");
        // Extremely dangerous!
        (bool success, ) = target.delegatecall(data);
        require(success);
    }
}
