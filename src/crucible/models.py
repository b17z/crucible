"""Data models for crucible."""

from dataclasses import dataclass
from enum import Enum


class Domain(Enum):
    """Code domain classification."""

    SMART_CONTRACT = "smart_contract"
    FRONTEND = "frontend"
    BACKEND = "backend"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class Severity(Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class ToolFinding:
    """A finding from a static analysis tool."""

    tool: str
    rule: str
    severity: Severity
    message: str
    location: str
    suggestion: str | None = None


# Domain detection heuristics
DOMAIN_HEURISTICS: dict[Domain, dict[str, list[str]]] = {
    Domain.SMART_CONTRACT: {
        "extensions": [".sol"],
        "imports": ["@openzeppelin", "hardhat", "foundry", "forge-std"],
        "markers": ["pragma solidity", "contract ", "function ", "modifier "],
    },
    Domain.FRONTEND: {
        "extensions": [".tsx", ".jsx", ".vue", ".svelte"],
        "imports": ["react", "next", "vue", "svelte", "@tanstack"],
        "markers": ["use client", "use server", "useState", "useEffect"],
    },
    Domain.BACKEND: {
        "extensions": [".py", ".go", ".rs"],
        "imports": ["fastapi", "flask", "django", "gin", "axum", "actix"],
        "markers": ["@app.route", "@router", "def ", "func ", "fn "],
    },
    Domain.INFRASTRUCTURE: {
        "extensions": [".tf", ".yaml", ".yml", ".toml"],
        "imports": [],
        "markers": ["resource ", "provider ", "apiVersion:", "kind:"],
    },
}


@dataclass(frozen=True)
class FullReviewResult:
    """Result from full_review tool."""

    domains_detected: tuple[str, ...]
    severity_summary: dict[str, int]
    findings: tuple[ToolFinding, ...]
    applicable_skills: tuple[str, ...]
    skill_triggers_matched: dict[str, tuple[str, ...]]
    principles_loaded: tuple[str, ...]
    principles_content: str
    sage_knowledge: str | None = None
    sage_query_used: str | None = None
