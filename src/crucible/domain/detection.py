"""Domain detection from code content and file paths."""

from pathlib import Path

from crucible.errors import Result, ok
from crucible.models import DOMAIN_HEURISTICS, Domain


def detect_domain_from_extension(file_path: str) -> Domain | None:
    """Detect domain from file extension."""
    ext = Path(file_path).suffix.lower()
    for domain, heuristics in DOMAIN_HEURISTICS.items():
        if ext in heuristics.get("extensions", []):
            return domain
    return None


def detect_domain_from_content(content: str) -> Domain | None:
    """Detect domain from code content markers and imports."""
    content_lower = content.lower()

    for domain, heuristics in DOMAIN_HEURISTICS.items():
        # Check imports
        for imp in heuristics.get("imports", []):
            if imp.lower() in content_lower:
                return domain

        # Check markers
        for marker in heuristics.get("markers", []):
            if marker.lower() in content_lower:
                return domain

    return None


def detect_domain(
    code: str,
    file_path: str | None = None,
) -> Result[Domain, str]:
    """
    Detect the domain of code.

    Priority:
    1. File extension (most reliable)
    2. Content markers and imports
    3. Unknown (fallback)

    Args:
        code: The source code content
        file_path: Optional file path for extension-based detection

    Returns:
        Result containing detected Domain or error message
    """
    # Try extension first
    if file_path:
        domain = detect_domain_from_extension(file_path)
        if domain:
            return ok(domain)

    # Try content detection
    domain = detect_domain_from_content(code)
    if domain:
        return ok(domain)

    # Fallback to unknown
    return ok(Domain.UNKNOWN)
