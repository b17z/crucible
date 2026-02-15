"""History management for session continuity.

Saves and loads review findings between sessions for context injection.
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crucible.enforcement.models import EnforcementFinding


HISTORY_DIR = Path(".crucible") / "history"
RECENT_FINDINGS_FILE = HISTORY_DIR / "recent-findings.md"


@dataclass(frozen=True)
class ReviewSummary:
    """Summary of a review for session context."""

    path: str
    when: datetime
    total_findings: int
    findings_by_severity: dict[str, int]
    top_findings: list[tuple[str, str, str, str]]  # (assertion_id, message, location, severity)


def save_recent_findings(
    findings: list["EnforcementFinding"],
    path: str,
    repo_root: str | None = None,
) -> Path | None:
    """Save review findings for session continuity.

    Creates .crucible/history/recent-findings.md with the last review results.
    This file is read by the SessionStart hook to provide context.

    Args:
        findings: List of enforcement findings from the review
        path: The path that was reviewed
        repo_root: Optional repository root for relative paths

    Returns:
        Path to the saved file, or None if no findings to save
    """
    base_path = Path(repo_root) if repo_root else Path(".")
    history_dir = base_path / HISTORY_DIR
    recent_file = base_path / RECENT_FINDINGS_FILE

    # Filter to active (non-suppressed) findings
    active_findings = [f for f in findings if not f.suppressed]

    if not active_findings:
        # Clear old findings if no new issues
        if recent_file.exists():
            recent_file.unlink()
        return None

    # Create history directory
    history_dir.mkdir(parents=True, exist_ok=True)

    # Build markdown content
    parts = [
        "# Last Review\n",
        f"**Path:** `{path}`  ",
        f"**When:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Issues:** {len(active_findings)}\n",
    ]

    # Group by severity
    by_severity: dict[str, list] = {}
    for f in active_findings:
        by_severity.setdefault(f.severity.upper(), []).append(f)

    # Add findings by severity
    for sev in ["ERROR", "WARNING", "INFO"]:
        items = by_severity.get(sev, [])
        if items:
            parts.append(f"\n## {sev} ({len(items)})\n")
            # Limit to top 5 per severity to avoid overly long context
            for f in items[:5]:
                parts.append(f"- **{f.assertion_id}**: {f.message}")
                parts.append(f"  - `{f.location}`")
            if len(items) > 5:
                parts.append(f"- ... and {len(items) - 5} more")

    recent_file.write_text("\n".join(parts))
    return recent_file


def load_recent_findings(repo_root: str | None = None) -> str | None:
    """Load recent findings markdown for context injection.

    Args:
        repo_root: Optional repository root

    Returns:
        Markdown content of recent findings, or None if not found
    """
    base_path = Path(repo_root) if repo_root else Path(".")
    recent_file = base_path / RECENT_FINDINGS_FILE

    if not recent_file.exists():
        return None

    try:
        content = recent_file.read_text()
        return content if content.strip() else None
    except OSError:
        return None


def clear_recent_findings(repo_root: str | None = None) -> bool:
    """Clear the recent findings file.

    Args:
        repo_root: Optional repository root

    Returns:
        True if file was removed, False if it didn't exist
    """
    base_path = Path(repo_root) if repo_root else Path(".")
    recent_file = base_path / RECENT_FINDINGS_FILE

    if recent_file.exists():
        recent_file.unlink()
        return True
    return False
