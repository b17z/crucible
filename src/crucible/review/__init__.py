"""Core review functionality shared between CLI and MCP."""

from crucible.review.core import (
    compute_severity_counts,
    deduplicate_findings,
    detect_domain,
    filter_findings_to_changes,
    get_tools_for_domain,
    load_skills_and_knowledge,
    run_enforcement,
    run_static_analysis,
)

__all__ = [
    "compute_severity_counts",
    "deduplicate_findings",
    "detect_domain",
    "filter_findings_to_changes",
    "get_tools_for_domain",
    "load_skills_and_knowledge",
    "run_enforcement",
    "run_static_analysis",
]
