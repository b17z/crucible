"""Skill loading and matching for full_review.

Skills follow cascade resolution:
1. Project: .crucible/skills/
2. User: ~/.claude/crucible/skills/
3. Bundled: package skills/
"""

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from crucible.errors import Result, err, ok
from crucible.models import Domain

# Skill directories (cascade priority)
SKILLS_BUNDLED = Path(__file__).parent
SKILLS_USER = Path.home() / ".claude" / "crucible" / "skills"
SKILLS_PROJECT = Path(".crucible") / "skills"


@dataclass(frozen=True)
class SkillMetadata:
    """Parsed skill frontmatter metadata."""

    name: str
    version: str
    triggers: tuple[str, ...]
    always_run: bool
    always_run_for_domains: tuple[str, ...]
    knowledge: tuple[str, ...]


def parse_skill_frontmatter(content: str) -> Result[SkillMetadata, str]:
    """Parse YAML frontmatter from skill markdown content.

    Args:
        content: Full skill file content with frontmatter

    Returns:
        Result containing SkillMetadata or error message
    """
    # Check for frontmatter delimiters
    if not content.startswith("---"):
        return err("No frontmatter found (file must start with ---)")

    # Find the closing delimiter
    end_match = re.search(r"\n---\s*\n", content)
    if not end_match:
        return err("No closing frontmatter delimiter found")

    frontmatter = content[3 : end_match.start()]

    # Parse simple YAML (we don't need a full parser for this format)
    data: dict[str, str | list[str] | bool] = {}

    for line in frontmatter.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()

        # Handle list values: [item1, item2, ...]
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            data[key] = [item.strip() for item in items if item.strip()]
        # Handle boolean values
        elif value.lower() == "true":
            data[key] = True
        elif value.lower() == "false":
            data[key] = False
        # Handle quoted strings
        elif value.startswith('"') and value.endswith('"'):
            data[key] = value[1:-1]
        else:
            data[key] = value

    # Build SkillMetadata
    version = data.get("version", "1.0")
    if isinstance(version, list):
        version = version[0] if version else "1.0"

    triggers_raw = data.get("triggers", [])
    triggers = tuple(triggers_raw) if isinstance(triggers_raw, list) else ()

    always_run = data.get("always_run", False)
    if not isinstance(always_run, bool):
        always_run = False

    always_run_for_domains_raw = data.get("always_run_for_domains", [])
    always_run_for_domains = (
        tuple(always_run_for_domains_raw)
        if isinstance(always_run_for_domains_raw, list)
        else ()
    )

    knowledge_raw = data.get("knowledge", [])
    knowledge = tuple(knowledge_raw) if isinstance(knowledge_raw, list) else ()

    return ok(
        SkillMetadata(
            name="",  # Will be set by load_skill
            version=str(version),
            triggers=triggers,
            always_run=always_run,
            always_run_for_domains=always_run_for_domains,
            knowledge=knowledge,
        )
    )


def resolve_skill_path(skill_name: str) -> tuple[Path | None, str]:
    """Find skill directory with cascade priority.

    Returns (path, source) where source is 'project', 'user', or 'bundled'.
    """
    # 1. Project-level (highest priority)
    project_path = SKILLS_PROJECT / skill_name / "SKILL.md"
    if project_path.exists():
        return project_path, "project"

    # 2. User-level
    user_path = SKILLS_USER / skill_name / "SKILL.md"
    if user_path.exists():
        return user_path, "user"

    # 3. Bundled (lowest priority)
    bundled_path = SKILLS_BUNDLED / skill_name / "SKILL.md"
    if bundled_path.exists():
        return bundled_path, "bundled"

    return None, ""


def get_all_skill_names() -> set[str]:
    """Get all available skill names from all sources."""
    names: set[str] = set()

    for source_dir in [SKILLS_BUNDLED, SKILLS_USER, SKILLS_PROJECT]:
        if source_dir.exists():
            for item in source_dir.iterdir():
                if item.is_dir() and (item / "SKILL.md").exists():
                    names.add(item.name)

    return names


@lru_cache(maxsize=64)
def _load_skill_cached(skill_name: str, path_str: str) -> tuple[SkillMetadata, str] | str:
    """Internal cached skill loader.

    Returns tuple on success, error string on failure.
    Using path_str as cache key to invalidate on path changes.
    """
    path = Path(path_str)
    content = path.read_text()
    result = parse_skill_frontmatter(content)

    if result.is_err:
        return f"Failed to parse skill '{skill_name}': {result.error}"

    metadata = SkillMetadata(
        name=skill_name,
        version=result.value.version,
        triggers=result.value.triggers,
        always_run=result.value.always_run,
        always_run_for_domains=result.value.always_run_for_domains,
        knowledge=result.value.knowledge,
    )

    return (metadata, content)


def load_skill(skill_name: str) -> Result[tuple[SkillMetadata, str], str]:
    """Load a skill by name with cascade resolution.

    Results are cached to avoid repeated file reads.

    Args:
        skill_name: Name of the skill directory (e.g., "security-engineer")

    Returns:
        Result containing (metadata, content) tuple or error message
    """
    path, source = resolve_skill_path(skill_name)
    if path is None:
        available = get_all_skill_names()
        if available:
            return err(f"Skill '{skill_name}' not found. Available: {', '.join(sorted(available))}")
        return err(f"Skill '{skill_name}' not found and no skills available")

    cached = _load_skill_cached(skill_name, str(path))
    if isinstance(cached, str):
        return err(cached)
    return ok(cached)


def clear_skill_cache() -> None:
    """Clear the skill loading cache. Useful for testing or after skill updates."""
    _load_skill_cached.cache_clear()


def match_skills_for_domain(
    domain: Domain,
    domain_tags: list[str],
    override: list[str] | None = None,
) -> list[tuple[str, list[str]]]:
    """Find skills that match the given domain and tags.

    Args:
        domain: Detected code domain
        domain_tags: Tags from domain detection (e.g., ["python", "backend"])
        override: Optional explicit skill list (skips matching logic)

    Returns:
        List of (skill_name, matched_triggers) tuples
    """
    # If explicit override, just return those skills
    if override:
        return [(name, ["explicit"]) for name in override]

    matched: list[tuple[str, list[str]]] = []
    domain_value = domain.value  # e.g., "smart_contract"

    for skill_name in get_all_skill_names():
        result = load_skill(skill_name)
        if result.is_err:
            continue

        metadata, _ = result.value
        triggers_matched: list[str] = []

        # Rule 1: always_run = true → always include
        if metadata.always_run:
            triggers_matched.append("always_run")

        # Rule 2: always_run_for_domains contains the domain → include
        if domain_value in metadata.always_run_for_domains:
            triggers_matched.append(f"always_run_for_domains:{domain_value}")

        # Rule 3: triggers intersect with domain_tags → include
        trigger_set = set(metadata.triggers)
        tag_set = set(domain_tags)
        intersection = trigger_set & tag_set
        if intersection:
            triggers_matched.extend(sorted(intersection))

        if triggers_matched:
            matched.append((skill_name, triggers_matched))

    # Sort by skill name for consistent ordering
    return sorted(matched, key=lambda x: x[0])


def get_knowledge_for_skills(skill_names: list[str]) -> set[str]:
    """Collect all knowledge files referenced by the given skills.

    Args:
        skill_names: List of skill names to check

    Returns:
        Set of knowledge file names (e.g., {"SECURITY.md", "SMART_CONTRACT.md"})
    """
    knowledge_files: set[str] = set()

    for skill_name in skill_names:
        result = load_skill(skill_name)
        if result.is_err:
            continue

        metadata, _ = result.value
        knowledge_files.update(metadata.knowledge)

    return knowledge_files
