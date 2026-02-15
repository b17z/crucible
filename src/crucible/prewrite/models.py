"""Data models for pre-write review."""

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class PrewriteMetadata:
    """Parsed template frontmatter."""

    name: str
    version: str = "1.0"
    description: str = ""
    checklist: tuple[str, ...] = ()
    knowledge: tuple[str, ...] = ()
    assertions: tuple[str, ...] = ()

    @classmethod
    def from_frontmatter(cls, data: dict, filename: str) -> "PrewriteMetadata":
        """Create metadata from parsed frontmatter dict."""
        # Handle checklist as list
        checklist_raw = data.get("checklist", [])
        if isinstance(checklist_raw, str):
            checklist_raw = [checklist_raw]

        # Handle knowledge as list
        knowledge_raw = data.get("knowledge", [])
        if isinstance(knowledge_raw, str):
            knowledge_raw = [knowledge_raw]

        # Handle assertions as list
        assertions_raw = data.get("assertions", [])
        if isinstance(assertions_raw, str):
            assertions_raw = [assertions_raw]

        return cls(
            name=data.get("name", filename.replace(".md", "").replace("-", " ").title()),
            version=str(data.get("version", "1.0")),
            description=data.get("description", ""),
            checklist=tuple(checklist_raw),
            knowledge=tuple(knowledge_raw),
            assertions=tuple(assertions_raw),
        )


@dataclass(frozen=True)
class PrewriteFinding:
    """A finding from pre-write review."""

    assertion_id: str
    message: str
    severity: Literal["error", "warning", "info"]
    reasoning: str | None = None
    location: str = "document"


@dataclass
class PrewriteResult:
    """Result of a pre-write review."""

    path: str
    template: str | None
    findings: list[PrewriteFinding] = field(default_factory=list)
    checklist: list[str] = field(default_factory=list)
    knowledge_loaded: list[str] = field(default_factory=list)
    skills_loaded: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    tokens_used: int = 0

    @property
    def passed(self) -> bool:
        """Check if review passed (no error-level findings)."""
        return not any(f.severity == "error" for f in self.findings)

    @property
    def error_count(self) -> int:
        """Count error-level findings."""
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count warning-level findings."""
        return sum(1 for f in self.findings if f.severity == "warning")

    @property
    def info_count(self) -> int:
        """Count info-level findings."""
        return sum(1 for f in self.findings if f.severity == "info")
