"""Data models for the enforcement module."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal


class AssertionType(Enum):
    """Type of assertion check."""

    PATTERN = "pattern"
    LLM = "llm"


class Priority(Enum):
    """Assertion priority levels for budget management."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        """Return numeric rank for sorting (lower = higher priority)."""
        return {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }[self]


@dataclass(frozen=True)
class Applicability:
    """Applicability configuration for an assertion."""

    glob: str | None = None
    exclude: tuple[str, ...] = ()


@dataclass(frozen=True)
class Assertion:
    """A single assertion rule."""

    id: str
    type: AssertionType
    message: str
    severity: Literal["error", "warning", "info"]
    priority: Priority
    pattern: str | None = None  # For pattern assertions
    languages: tuple[str, ...] = ()
    applicability: Applicability | None = None
    compliance: str | None = None  # For LLM assertions (v0.5+)
    model: str | None = None  # For LLM assertions (v0.5+)


@dataclass(frozen=True)
class AssertionFile:
    """A parsed assertion file."""

    version: str
    name: str
    description: str
    assertions: tuple[Assertion, ...]
    source: str  # "project", "user", or "bundled"
    path: str  # File path for error reporting


@dataclass(frozen=True)
class PatternMatch:
    """A pattern match result."""

    assertion_id: str
    line: int
    column: int
    match_text: str
    file_path: str

    @property
    def location(self) -> str:
        """Return location string in standard format."""
        return f"{self.file_path}:{self.line}:{self.column}"


@dataclass(frozen=True)
class Suppression:
    """An inline suppression comment."""

    line: int
    rule_ids: tuple[str, ...]
    reason: str | None
    applies_to_next_line: bool


@dataclass(frozen=True)
class EnforcementFinding:
    """A finding from enforcement checking."""

    assertion_id: str
    message: str
    severity: Literal["error", "warning", "info"]
    priority: Priority
    location: str
    match_text: str | None = None
    suppressed: bool = False
    suppression_reason: str | None = None
