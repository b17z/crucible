// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// BAD: Classic reentrancy vulnerability
contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // BAD: State change AFTER external call (violates CEI pattern)
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "No balance");

        // BAD: External call before state update
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Transfer failed");

        // State change after external call - REENTRANCY!
        balances[msg.sender] = 0;
    }

    // BAD: No reentrancy guard on value transfer
    function withdrawAll() external {
        uint256 amount = balances[msg.sender];
        balances[msg.sender] = 0;  // Good: state change first

        // But still missing reentrancy guard for defense in depth
        payable(msg.sender).transfer(amount);
    }
}
