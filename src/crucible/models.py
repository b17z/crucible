"""Data models for crucible."""

from dataclasses import dataclass, field
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


class Persona(Enum):
    """Reviewer personas."""

    SECURITY = "security"
    WEB3 = "web3"
    BACKEND = "backend"
    DEVOPS = "devops"
    PRODUCT = "product"
    PERFORMANCE = "performance"
    DATA = "data"
    ACCESSIBILITY = "accessibility"
    MOBILE = "mobile"
    UIUX = "uiux"
    FDE = "fde"
    CUSTOMER_SUCCESS = "customer_success"
    TECH_LEAD = "tech_lead"
    PRAGMATIST = "pragmatist"
    PURIST = "purist"
    # Smart contract specific
    GAS_OPTIMIZER = "gas_optimizer"
    PROTOCOL_ARCHITECT = "protocol_architect"
    MEV_RESEARCHER = "mev_researcher"
    FORMAL_VERIFICATION = "formal_verification"
    INCIDENT_RESPONDER = "incident_responder"


@dataclass(frozen=True)
class ToolFinding:
    """A finding from a static analysis tool."""

    tool: str
    rule: str
    severity: Severity
    message: str
    location: str
    suggestion: str | None = None


@dataclass(frozen=True)
class PersonaReview:
    """A review from a single persona."""

    persona: Persona
    verdict: str  # "approve", "request_changes", "comment"
    concerns: tuple[str, ...] = field(default_factory=tuple)
    approvals: tuple[str, ...] = field(default_factory=tuple)
    questions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Tension:
    """A disagreement between personas."""

    personas: tuple[Persona, Persona]
    topic: str
    position_a: str
    position_b: str
    resolution_hint: str | None = None


@dataclass(frozen=True)
class ReviewResult:
    """Complete review result."""

    domain: Domain
    tool_findings: tuple[ToolFinding, ...] = field(default_factory=tuple)
    persona_reviews: tuple[PersonaReview, ...] = field(default_factory=tuple)
    tensions: tuple[Tension, ...] = field(default_factory=tuple)
    synthesis: str = ""
    checklist: tuple[str, ...] = field(default_factory=tuple)


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


# Persona routing by domain
PERSONA_ROUTING: dict[Domain, list[Persona]] = {
    Domain.SMART_CONTRACT: [
        Persona.SECURITY,
        Persona.WEB3,
        Persona.GAS_OPTIMIZER,
        Persona.PROTOCOL_ARCHITECT,
        Persona.MEV_RESEARCHER,
        Persona.INCIDENT_RESPONDER,
    ],
    Domain.FRONTEND: [
        Persona.PRODUCT,
        Persona.ACCESSIBILITY,
        Persona.UIUX,
        Persona.PERFORMANCE,
        Persona.MOBILE,
    ],
    Domain.BACKEND: [
        Persona.SECURITY,
        Persona.BACKEND,
        Persona.DATA,
        Persona.DEVOPS,
        Persona.PERFORMANCE,
    ],
    Domain.INFRASTRUCTURE: [
        Persona.DEVOPS,
        Persona.SECURITY,
        Persona.PERFORMANCE,
    ],
    Domain.UNKNOWN: [
        Persona.SECURITY,
        Persona.PRAGMATIST,
    ],
}
