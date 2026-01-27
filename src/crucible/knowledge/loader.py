"""Load engineering principles from markdown files.

Knowledge follows the same cascade as skills:
1. Project: .crucible/knowledge/
2. User: ~/.claude/crucible/knowledge/
3. Bundled: package knowledge/
"""

from pathlib import Path

from crucible.errors import Result, err, ok

# Knowledge directories (same pattern as skills)
KNOWLEDGE_BUNDLED = Path(__file__).parent / "principles"
KNOWLEDGE_USER = Path.home() / ".claude" / "crucible" / "knowledge"
KNOWLEDGE_PROJECT = Path(".crucible") / "knowledge"


def load_knowledge_file(filename: str) -> Result[str, str]:
    """Load a single knowledge file by name.

    Args:
        filename: Knowledge file name (e.g., "SECURITY.md")

    Returns:
        Result containing file content or error message
    """
    path, source = resolve_knowledge_file(filename)
    if path is None:
        return err(f"Knowledge file '{filename}' not found")

    try:
        return ok(path.read_text())
    except OSError as e:
        return err(f"Failed to read '{filename}': {e}")


def resolve_knowledge_file(filename: str) -> tuple[Path | None, str]:
    """Find knowledge file with cascade priority.

    Returns (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # 1. Project-level (highest priority)
    project_path = KNOWLEDGE_PROJECT / filename
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = KNOWLEDGE_USER / filename
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = KNOWLEDGE_BUNDLED / filename
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_knowledge_files() -> set[str]:
    """Get all available knowledge file names from all sources."""
    files: set[str] = set()

    for source_dir in [KNOWLEDGE_BUNDLED, KNOWLEDGE_USER, KNOWLEDGE_PROJECT]:
        if source_dir.exists():
            for file_path in source_dir.iterdir():
                if file_path.is_file() and file_path.suffix == ".md":
                    files.add(file_path.name)

    return files


def get_custom_knowledge_files() -> set[str]:
    """Get knowledge files from project and user directories only.

    These are custom/team knowledge files that should always be included
    in full_review, regardless of skill references.

    Returns:
        Set of filenames from project and user knowledge directories
    """
    files: set[str] = set()

    for source_dir in [KNOWLEDGE_USER, KNOWLEDGE_PROJECT]:
        if source_dir.exists():
            for file_path in source_dir.iterdir():
                if file_path.is_file() and file_path.suffix == ".md":
                    files.add(file_path.name)

    return files


def load_all_knowledge(
    include_bundled: bool = False,
    filenames: set[str] | None = None,
) -> tuple[list[str], str]:
    """Load multiple knowledge files.

    Args:
        include_bundled: If True, include bundled knowledge files
        filenames: Specific files to load (if None, loads based on include_bundled)

    Returns:
        Tuple of (list of loaded filenames, combined content)
    """
    if filenames is None:
        filenames = get_all_knowledge_files() if include_bundled else get_custom_knowledge_files()

    loaded: list[str] = []
    parts: list[str] = []

    for filename in sorted(filenames):
        result = load_knowledge_file(filename)
        if result.is_ok:
            loaded.append(filename)
            parts.append(f"# {filename}\n\n{result.value}")

    content = "\n\n---\n\n".join(parts) if parts else ""
    return loaded, content


def load_principles(topic: str | None = None) -> Result[str, str]:
    """
    Load engineering principles from markdown files.

    Args:
        topic: Optional topic filter (e.g., "security", "smart_contract", "engineering")

    Returns:
        Result containing principles content or error message
    """
    # Map topics to domain-specific files
    topic_files = {
        None: ["SECURITY.md", "TESTING.md"],  # Default: security + testing basics
        "engineering": ["TESTING.md", "ERROR_HANDLING.md", "TYPE_SAFETY.md"],
        "security": ["SECURITY.md", "GITIGNORE.md", "PRECOMMIT.md"],
        "smart_contract": ["SMART_CONTRACT.md"],
        "checklist": ["SECURITY.md", "TESTING.md", "ERROR_HANDLING.md"],
        "repo_hygiene": ["GITIGNORE.md", "PRECOMMIT.md", "COMMITS.md"],
    }

    files_to_load = topic_files.get(topic, topic_files[None])
    content_parts: list[str] = []

    for filename in files_to_load:
        path, _source = resolve_knowledge_file(filename)
        if path and path.exists():
            content_parts.append(path.read_text())

    if not content_parts:
        available = get_all_knowledge_files()
        if available:
            return err(f"No principles found for topic: {topic}. Available files: {', '.join(sorted(available))}")
        return err("No knowledge files found. Run 'crucible knowledge list' to see available topics.")

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
