"""Load engineering principles from markdown files.

Knowledge follows the same cascade as skills:
1. Project: .crucible/knowledge/
2. User: ~/.claude/crucible/knowledge/
3. Bundled: package knowledge/

Knowledge files support frontmatter for better Claude Code integration:
---
name: Security Principles
description: Core security principles for all code
triggers: [security, auth, crypto]
type: principle  # principle | pattern | preference
assertions: security.yaml  # linked assertion file
---
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from crucible.errors import Result, err, ok


@dataclass(frozen=True)
class KnowledgeMetadata:
    """Metadata parsed from knowledge file frontmatter."""

    name: str
    description: str = ""
    triggers: tuple[str, ...] = ()
    type: str = "principle"  # principle, pattern, preference
    assertions: str | None = None  # linked assertion file

    @classmethod
    def from_frontmatter(cls, data: dict, filename: str) -> "KnowledgeMetadata":
        """Create metadata from parsed frontmatter dict."""
        return cls(
            name=data.get("name", filename.replace(".md", "").replace("_", " ").title()),
            description=data.get("description", ""),
            triggers=tuple(data.get("triggers", [])),
            type=data.get("type", "principle"),
            assertions=data.get("assertions"),
        )


@dataclass
class KnowledgeFile:
    """A knowledge file with metadata and content."""

    filename: str
    path: Path
    source: str  # project, user, bundled
    metadata: KnowledgeMetadata
    content: str = field(repr=False)


def parse_frontmatter(content: str, filename: str) -> tuple[KnowledgeMetadata, str]:
    """Parse YAML frontmatter from knowledge file content.

    Args:
        content: Full file content
        filename: Filename for default metadata

    Returns:
        Tuple of (metadata, content without frontmatter)
    """
    if not content.startswith("---"):
        # No frontmatter, return defaults
        return KnowledgeMetadata(name=filename.replace(".md", "").replace("_", " ").title()), content

    # Find closing ---
    lines = content.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        # Malformed frontmatter, treat as no frontmatter
        return KnowledgeMetadata(name=filename.replace(".md", "").replace("_", " ").title()), content

    # Parse YAML
    frontmatter_text = "\n".join(lines[1:end_idx])
    remaining_content = "\n".join(lines[end_idx + 1 :]).lstrip()

    try:
        data = yaml.safe_load(frontmatter_text) or {}
        metadata = KnowledgeMetadata.from_frontmatter(data, filename)
    except yaml.YAMLError:
        metadata = KnowledgeMetadata(name=filename.replace(".md", "").replace("_", " ").title())

    return metadata, remaining_content

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


def load_knowledge_with_metadata(filename: str) -> Result[KnowledgeFile, str]:
    """Load a knowledge file with parsed metadata.

    Args:
        filename: Knowledge file name (e.g., "SECURITY.md")

    Returns:
        Result containing KnowledgeFile or error message
    """
    path, source = resolve_knowledge_file(filename)
    if path is None:
        return err(f"Knowledge file '{filename}' not found")

    try:
        raw_content = path.read_text()
        metadata, content = parse_frontmatter(raw_content, filename)
        return ok(
            KnowledgeFile(
                filename=filename,
                path=path,
                source=source,
                metadata=metadata,
                content=content,
            )
        )
    except OSError as e:
        return err(f"Failed to read '{filename}': {e}")


def get_all_knowledge_metadata() -> list[tuple[str, KnowledgeMetadata]]:
    """Get metadata for all knowledge files (for discovery/indexing).

    Returns list of (filename, metadata) tuples. This is cheap - only parses
    frontmatter, doesn't load full content into memory.
    """
    results: list[tuple[str, KnowledgeMetadata]] = []

    for filename in sorted(get_all_knowledge_files()):
        path, _ = resolve_knowledge_file(filename)
        if path:
            try:
                # Read just enough to get frontmatter
                content = path.read_text()
                metadata, _ = parse_frontmatter(content, filename)
                results.append((filename, metadata))
            except OSError:
                # Skip unreadable files
                pass

    return results


def get_knowledge_by_trigger(trigger: str) -> list[str]:
    """Get knowledge files that match a trigger.

    Args:
        trigger: Trigger to match (e.g., "security", "auth")

    Returns:
        List of matching filenames
    """
    matches: list[str] = []
    trigger_lower = trigger.lower()

    for filename, metadata in get_all_knowledge_metadata():
        if trigger_lower in [t.lower() for t in metadata.triggers]:
            matches.append(filename)

    return matches


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


def get_linked_assertion_files(knowledge_files: set[str] | None = None) -> set[str]:
    """Get assertion files linked to knowledge files.

    Looks at the `assertions` field in knowledge frontmatter to find
    linked assertion files that should be loaded.

    Args:
        knowledge_files: Specific knowledge files to check (if None, checks all)

    Returns:
        Set of assertion filenames to load
    """
    if knowledge_files is None:
        knowledge_files = get_all_knowledge_files()

    assertion_files: set[str] = set()

    for filename in knowledge_files:
        path, _ = resolve_knowledge_file(filename)
        if path:
            try:
                content = path.read_text()
                metadata, _ = parse_frontmatter(content, filename)
                if metadata.assertions:
                    assertion_files.add(metadata.assertions)
            except OSError:
                pass

    return assertion_files


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
