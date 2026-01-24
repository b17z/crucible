"""Load engineering principles from markdown files."""

from pathlib import Path

from crucible.errors import Result, err, ok


def find_knowledge_dir() -> Path | None:
    """Find the knowledge directory, checking project then package."""
    # Check project-local first
    project_knowledge = Path.cwd() / "knowledge"
    if project_knowledge.is_dir():
        return project_knowledge

    # Check package directory
    package_knowledge = Path(__file__).parent.parent.parent.parent / "knowledge"
    if package_knowledge.is_dir():
        return package_knowledge

    return None


def load_principles(topic: str | None = None) -> Result[str, str]:
    """
    Load engineering principles from markdown files.

    Args:
        topic: Optional topic filter (e.g., "security", "smart_contract")

    Returns:
        Result containing principles content or error message
    """
    knowledge_dir = find_knowledge_dir()
    if not knowledge_dir:
        return err("Knowledge directory not found")

    # Map topics to files
    topic_files = {
        None: ["ENGINEERING_PRINCIPLES.md"],
        "engineering": ["ENGINEERING_PRINCIPLES.md"],
        "security": ["SENIOR_ENGINEER_CHECKLIST.md"],
        "smart_contract": [
            "SENIOR_ENGINEER_CHECKLIST.md",
        ],
        "checklist": ["SENIOR_ENGINEER_CHECKLIST.md"],
    }

    files_to_load = topic_files.get(topic, topic_files[None])
    content_parts: list[str] = []

    for filename in files_to_load:
        filepath = knowledge_dir / filename
        if filepath.exists():
            content_parts.append(filepath.read_text())

    if not content_parts:
        return err(f"No principles found for topic: {topic}")

    return ok("\n\n---\n\n".join(content_parts))


def get_persona_section(persona: str, content: str) -> str | None:
    """
    Extract a specific persona section from the checklist content.

    Args:
        persona: Persona name (e.g., "security", "web3")
        content: Full checklist markdown content

    Returns:
        The persona section content or None if not found
    """
    # Normalize persona name for matching
    persona_headers = {
        "security": "## Security Engineer",
        "web3": "## Web3/Blockchain Engineer",
        "backend": "## Backend/Systems Engineer",
        "devops": "## DevOps/SRE",
        "product": "## Product Engineer",
        "performance": "## Performance Engineer",
        "data": "## Data Engineer",
        "accessibility": "## Accessibility Engineer",
        "mobile": "## Mobile/Client Engineer",
        "uiux": "## UI/UX Designer",
        "fde": "## Forward Deployed",
        "customer_success": "## Customer Success",
        "tech_lead": "## Tech Lead",
        "pragmatist": "## Pragmatist",
        "purist": "## Purist",
    }

    header = persona_headers.get(persona.lower())
    if not header:
        return None

    # Find the section
    lines = content.split("\n")
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if header in line:
            start_idx = i
        elif start_idx is not None and line.startswith("## ") and i > start_idx:
            end_idx = i
            break

    if start_idx is None:
        return None

    end_idx = end_idx or len(lines)
    return "\n".join(lines[start_idx:end_idx])
