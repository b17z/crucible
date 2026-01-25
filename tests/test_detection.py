"""Tests for domain detection."""


from crucible.domain.detection import (
    detect_domain,
    detect_domain_from_content,
    detect_domain_from_extension,
)
from crucible.models import Domain


class TestDetectDomainFromExtension:
    """Test extension-based domain detection."""

    def test_solidity_file(self) -> None:
        assert detect_domain_from_extension("contract.sol") == Domain.SMART_CONTRACT
        assert detect_domain_from_extension("src/Vault.sol") == Domain.SMART_CONTRACT

    def test_frontend_files(self) -> None:
        assert detect_domain_from_extension("App.tsx") == Domain.FRONTEND
        assert detect_domain_from_extension("component.jsx") == Domain.FRONTEND
        assert detect_domain_from_extension("Page.vue") == Domain.FRONTEND

    def test_backend_files(self) -> None:
        assert detect_domain_from_extension("main.py") == Domain.BACKEND
        assert detect_domain_from_extension("server.go") == Domain.BACKEND
        assert detect_domain_from_extension("lib.rs") == Domain.BACKEND

    def test_infrastructure_files(self) -> None:
        assert detect_domain_from_extension("main.tf") == Domain.INFRASTRUCTURE
        assert detect_domain_from_extension("config.yaml") == Domain.INFRASTRUCTURE
        assert detect_domain_from_extension("deploy.yml") == Domain.INFRASTRUCTURE

    def test_unknown_extension(self) -> None:
        assert detect_domain_from_extension("readme.md") is None
        assert detect_domain_from_extension("data.json") is None


class TestDetectDomainFromContent:
    """Test content-based domain detection."""

    def test_solidity_pragma(self) -> None:
        code = "pragma solidity ^0.8.0;\ncontract Vault {}"
        assert detect_domain_from_content(code) == Domain.SMART_CONTRACT

    def test_openzeppelin_import(self) -> None:
        code = 'import "@openzeppelin/contracts/token/ERC20.sol";'
        assert detect_domain_from_content(code) == Domain.SMART_CONTRACT

    def test_react_import(self) -> None:
        code = "import React from 'react';\nimport { useState } from 'react';"
        assert detect_domain_from_content(code) == Domain.FRONTEND

    def test_fastapi_import(self) -> None:
        code = "from fastapi import FastAPI\napp = FastAPI()"
        assert detect_domain_from_content(code) == Domain.BACKEND

    def test_terraform_resource(self) -> None:
        code = 'resource "aws_instance" "web" {\n  ami = "ami-123"\n}'
        assert detect_domain_from_content(code) == Domain.INFRASTRUCTURE


class TestDetectDomain:
    """Test combined domain detection."""

    def test_extension_takes_priority(self) -> None:
        # Even with React content, .sol extension wins
        code = "import React from 'react';"
        result = detect_domain(code, "contract.sol")
        assert result.is_ok
        assert result.value == Domain.SMART_CONTRACT

    def test_content_fallback(self) -> None:
        code = "pragma solidity ^0.8.0;"
        result = detect_domain(code)  # No file path
        assert result.is_ok
        assert result.value == Domain.SMART_CONTRACT

    def test_unknown_fallback(self) -> None:
        code = "print('hello world')"
        result = detect_domain(code)
        assert result.is_ok
        assert result.value == Domain.UNKNOWN
