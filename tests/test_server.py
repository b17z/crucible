"""Tests for server internals."""

from crucible.models import Domain
from crucible.server import _detect_domain


class TestDetectDomain:
    """Test internal domain detection."""

    def test_solidity(self) -> None:
        domain, tags = _detect_domain("contract.sol")
        assert domain == Domain.SMART_CONTRACT
        assert "solidity" in tags
        assert "web3" in tags

    def test_vyper(self) -> None:
        domain, tags = _detect_domain("contract.vy")
        assert domain == Domain.SMART_CONTRACT
        assert "vyper" in tags
        assert "web3" in tags

    def test_python(self) -> None:
        domain, tags = _detect_domain("main.py")
        assert domain == Domain.BACKEND
        assert "python" in tags

    def test_typescript(self) -> None:
        domain, tags = _detect_domain("App.tsx")
        assert domain == Domain.FRONTEND
        assert "typescript" in tags

    def test_javascript(self) -> None:
        domain, tags = _detect_domain("index.js")
        assert domain == Domain.FRONTEND
        assert "javascript" in tags

    def test_go(self) -> None:
        domain, tags = _detect_domain("main.go")
        assert domain == Domain.BACKEND
        assert "go" in tags

    def test_rust(self) -> None:
        domain, tags = _detect_domain("lib.rs")
        assert domain == Domain.BACKEND
        assert "rust" in tags

    def test_terraform(self) -> None:
        domain, tags = _detect_domain("main.tf")
        assert domain == Domain.INFRASTRUCTURE
        assert "infrastructure" in tags
        assert "devops" in tags

    def test_yaml(self) -> None:
        domain, tags = _detect_domain("deploy.yaml")
        assert domain == Domain.INFRASTRUCTURE

    def test_unknown(self) -> None:
        domain, tags = _detect_domain("README.md")
        assert domain == Domain.UNKNOWN
        assert "unknown" in tags
