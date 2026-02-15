"""Load pre-write templates with cascade resolution.

Templates follow the same cascade as skills/knowledge:
1. Project: .crucible/templates/prewrite/
2. User: ~/.claude/crucible/templates/prewrite/
3. Bundled: package templates/prewrite/
"""

from pathlib import Path

import yaml

from crucible.errors import Result, err, ok
from crucible.prewrite.models import PrewriteMetadata

# Template directories (cascade priority)
TEMPLATES_BUNDLED = Path(__file__).parent.parent / "templates" / "prewrite"
TEMPLATES_USER = Path.home() / ".claude" / "crucible" / "templates" / "prewrite"
TEMPLATES_PROJECT = Path(".crucible") / "templates" / "prewrite"


def resolve_template_path(name: str) -> tuple[Path | None, str]:
    """Find template file with cascade priority.

    Args:
        name: Template name (e.g., "prd" or "prd.md")

    Returns:
        (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # Ensure .md extension
    if not name.endswith(".md"):
        name = f"{name}.md"

    # 1. Project-level (highest priority)
    project_path = TEMPLATES_PROJECT / name
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = TEMPLATES_USER / name
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = TEMPLATES_BUNDLED / name
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_template_names() -> set[str]:
    """Get all available template names from all sources."""
    names: set[str] = set()

    for source_dir in [TEMPLATES_BUNDLED, TEMPLATES_USER, TEMPLATES_PROJECT]:
        if source_dir.exists():
            for file_path in source_dir.iterdir():
                if file_path.is_file() and file_path.suffix == ".md":
                    # Return name without extension
                    names.add(file_path.stem)

    return names


def parse_template_frontmatter(content: str, filename: str) -> Result[tuple[PrewriteMetadata, str], str]:
    """Parse YAML frontmatter from template content.

    Args:
        content: Full file content
        filename: Filename for default metadata

    Returns:
        Result containing (metadata, content without frontmatter) or error
    """
    if not content.startswith("---"):
        # No frontmatter
        return ok((
            PrewriteMetadata(name=filename.replace(".md", "").replace("-", " ").title()),
            content,
        ))

    # Find closing ---
    lines = content.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return err(f"Malformed frontmatter in {filename}: no closing ---")

    # Parse YAML
    frontmatter_text = "\n".join(lines[1:end_idx])
    remaining_content = "\n".join(lines[end_idx + 1:]).lstrip()

    try:
        data = yaml.safe_load(frontmatter_text) or {}
        metadata = PrewriteMetadata.from_frontmatter(data, filename)
    except yaml.YAMLError as e:
        return err(f"Invalid YAML frontmatter in {filename}: {e}")

    return ok((metadata, remaining_content))


def load_template(name: str) -> Result[tuple[PrewriteMetadata, str], str]:
    """Load a template by name with cascade resolution.

    Args:
        name: Template name (e.g., "prd" or "prd.md")

    Returns:
        Result containing (metadata, full content with frontmatter) or error
    """
    path, source = resolve_template_path(name)
    if path is None:
        available = get_all_template_names()
        if available:
            return err(f"Template '{name}' not found. Available: {', '.join(sorted(available))}")
        return err(f"Template '{name}' not found. No templates available.")

    try:
        content = path.read_text()
    except OSError as e:
        return err(f"Failed to read template '{name}': {e}")

    # Parse frontmatter for metadata
    result = parse_template_frontmatter(content, path.name)
    if result.is_err:
        return err(result.error)

    metadata, body = result.value

    # Return full content (including frontmatter) for init command
    return ok((metadata, content))


def load_template_body(name: str) -> Result[tuple[PrewriteMetadata, str], str]:
    """Load a template and return just the body (without frontmatter).

    Args:
        name: Template name (e.g., "prd" or "prd.md")

    Returns:
        Result containing (metadata, body content without frontmatter) or error
    """
    path, source = resolve_template_path(name)
    if path is None:
        available = get_all_template_names()
        if available:
            return err(f"Template '{name}' not found. Available: {', '.join(sorted(available))}")
        return err(f"Template '{name}' not found. No templates available.")

    try:
        content = path.read_text()
    except OSError as e:
        return err(f"Failed to read template '{name}': {e}")

    return parse_template_frontmatter(content, path.name)


def detect_template_type(content: str) -> str | None:
    """Auto-detect template type from document content.

    Looks for common patterns that indicate document type.

    Args:
        content: Document content to analyze

    Returns:
        Template name if detected, None otherwise
    """
    content_lower = content.lower()

    # Check for explicit frontmatter type
    if content.startswith("---"):
        lines = content.split("\n")
        for line in lines[1:]:
            if line.strip() == "---":
                break
            if line.strip().startswith("name:"):
                name = line.split(":", 1)[1].strip().strip("'\"").lower()
                if name in ("prd", "tdd", "rfc", "adr", "security-review"):
                    return name

    # Heuristic detection based on content
    indicators = {
        "prd": ["product requirements", "user stories", "success metrics", "## problem statement"],
        "tdd": ["technical design", "architecture", "data model", "api contracts", "## detailed design"],
        "rfc": ["request for comments", "## motivation", "## rationale", "## drawbacks"],
        "adr": ["architecture decision record", "## status", "## decision", "## consequences"],
        "security-review": ["security review", "threat model", "## assets", "## threats"],
    }

    for template_type, keywords in indicators.items():
        matches = sum(1 for kw in keywords if kw in content_lower)
        if matches >= 2:
            return template_type

    return None
