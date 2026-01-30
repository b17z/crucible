"""Data models for the enforcement module."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class AssertionType(Enum):
    """Type of assertion check."""

    PATTERN = "pattern"
    LLM = "llm"


class OverflowBehavior(Enum):
    """Behavior when token budget is exceeded."""

    SKIP = "skip"  # Skip remaining assertions silently
    WARN = "warn"  # Skip with warning
    FAIL = "fail"  # Fail the review


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
    source: Literal["pattern", "llm"] = "pattern"
    llm_reasoning: str | None = None  # LLM's explanation for the finding


@dataclass(frozen=True)
class ComplianceConfig:
    """Configuration for LLM-based compliance checking."""

    enabled: bool = True
    model: str = "sonnet"  # Default model (sonnet or opus)
    token_budget: int = 10000  # 0 = unlimited
    priority_order: tuple[str, ...] = ("critical", "high", "medium", "low")
    overflow_behavior: OverflowBehavior = OverflowBehavior.WARN


@dataclass
class BudgetState:
    """Mutable state for tracking token budget during compliance run."""

    total_budget: int
    tokens_used: int = 0
    assertions_run: int = 0
    assertions_skipped: int = 0
    overflow_triggered: bool = False
    skipped_assertions: list[str] = field(default_factory=list)

    @property
    def tokens_remaining(self) -> int:
        """Tokens remaining in budget."""
        if self.total_budget == 0:
            return float("inf")  # type: ignore[return-value]
        return max(0, self.total_budget - self.tokens_used)

    @property
    def is_exhausted(self) -> bool:
        """Whether budget is exhausted."""
        if self.total_budget == 0:
            return False
        return self.tokens_used >= self.total_budget

    def consume(self, tokens: int) -> None:
        """Consume tokens from budget."""
        self.tokens_used += tokens
        self.assertions_run += 1

    def skip(self, assertion_id: str) -> None:
        """Record a skipped assertion."""
        self.assertions_skipped += 1
        self.skipped_assertions.append(assertion_id)
        self.overflow_triggered = True


@dataclass(frozen=True)
class LLMAssertionResult:
    """Result from running a single LLM assertion."""

    assertion_id: str
    passed: bool
    findings: tuple["EnforcementFinding", ...]
    tokens_used: int
    model_used: str
    error: str | None = None
