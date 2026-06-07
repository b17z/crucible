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


# Reverse-map for the v2-shim: v2 knowledge filenames → v1 names.
# The v1 knowledge loader still uses the flat src/crucible/knowledge/principles/
# location with uppercase filenames. v2 nests them under skills with
# kebab-case names. The shim translates so v1 callers loading knowledge
# by name (e.g. SECURITY.md) keep working.
# Files not in this map pass through unchanged (e.g. new v2-only knowledge
# like supply-chain-2026.md has no v1 counterpart).
_V2_KNOWLEDGE_TO_V1 = {
    "api-design.md": "API_DESIGN.md",
    "commits.md": "COMMITS.md",
    "database.md": "DATABASE.md",
    "documentation.md": "DOCUMENTATION.md",
    "error-handling.md": "ERROR_HANDLING.md",
    "functional-programming.md": "FP.md",
    "gitignore.md": "GITIGNORE.md",
    "observability.md": "OBSERVABILITY.md",
    "precommit.md": "PRECOMMIT.md",
    "security-principles.md": "SECURITY.md",
    "smart-contract.md": "SMART_CONTRACT.md",
    "system-design.md": "SYSTEM_DESIGN.md",
    "testing.md": "TESTING.md",
    "type-safety.md": "TYPE_SAFETY.md",
}


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


def _current_skills_spec():
    """Build a CascadeSpec from the module's current SKILLS_* constants.

    Reading the constants at call time (rather than import time) means
    test code that patches them — e.g. ``patch('crucible.skills.loader.SKILLS_PROJECT', tmp_path)`` —
    still flows through to the cascade resolver.
    """
    from crucible.skills_core import CascadeSpec

    return CascadeSpec(
        project_dir=SKILLS_PROJECT,
        user_dir=SKILLS_USER,
        bundled_dir=SKILLS_BUNDLED,
        is_folder=True,
        suffix=None,
    )


def resolve_skill_path(skill_name: str) -> tuple[Path | None, str]:
    """Find skill SKILL.md file with cascade priority.

    Returns (path-to-SKILL.md, source) where source is 'project', 'user',
    or 'bundled'. Returns (None, "") if not found.

    Phase 2: delegates to ``skills_core.resolve``. The v1 module-level
    SKILLS_BUNDLED/SKILLS_USER/SKILLS_PROJECT constants are read at call
    time, so test patches of those constants still take effect.
    """
    from crucible.skills_core import resolve

    spec = _current_skills_spec()
    result = resolve(spec, skill_name)
    if result.is_err:
        return None, ""
    resolved = result.value
    skill_md = resolved.path / "SKILL.md"
    if not skill_md.exists():
        return None, ""
    return skill_md, resolved.source


def get_all_skill_names() -> set[str]:
    """Get all available skill names from all sources.

    Phase 2: delegates to skills_core.list_available. Filters out names
    lacking a SKILL.md (skills_core's list_available counts all folders;
    v1 contract requires SKILL.md presence).
    """
    from crucible.skills_core import list_available

    spec = _current_skills_spec()
    candidates = list_available(spec)
    names: set[str] = set()
    for base in (SKILLS_PROJECT, SKILLS_USER, SKILLS_BUNDLED):
        if not base.exists():
            continue
        for name in candidates:
            if (base / name / "SKILL.md").exists():
                names.add(name)
    return names


def _extract_keywords_from_pattern(pattern: str) -> list[str]:
    """Extract flat-string keywords from a v2 prompt_match regex pattern.

    v2 patterns look like '\\b(security|auth(n|z)?|owasp)\\b'. The v1
    contract returns flat keyword strings used for set-intersection
    matching against domain tags. This extracts top-level alternations
    and individual word tokens.

    Approximation, not exact regex semantics — but covers every pattern
    Crucible's bundled triggers.yaml files actually use.

    Algorithm:
      1. Scan the pattern, tracking paren depth.
      2. For each top-level paren group, collect the inside.
      3. Split that group on top-level pipes (depth=0 inside the group).
      4. Strip each piece of regex metachars + character classes; keep
         what's left if it's a plain word.
    """
    import re

    keywords: list[str] = []

    # Manual paren-depth scan to extract top-level groups
    i = 0
    while i < len(pattern):
        if pattern[i] == "\\" and i + 1 < len(pattern):
            i += 2  # skip escape pair
            continue
        if pattern[i] == "(":
            # Find matching close paren
            depth = 1
            j = i + 1
            while j < len(pattern) and depth > 0:
                if pattern[j] == "\\" and j + 1 < len(pattern):
                    j += 2
                    continue
                if pattern[j] == "(":
                    depth += 1
                elif pattern[j] == ")":
                    depth -= 1
                j += 1
            if depth == 0:
                group_content = pattern[i + 1 : j - 1]
                # Split on top-level pipes (depth=0 within the group)
                pieces: list[str] = []
                buf = ""
                depth = 0
                k = 0
                while k < len(group_content):
                    c = group_content[k]
                    if c == "\\" and k + 1 < len(group_content):
                        buf += c + group_content[k + 1]
                        k += 2
                        continue
                    if c == "(":
                        depth += 1
                        buf += c
                    elif c == ")":
                        depth -= 1
                        buf += c
                    elif c == "|" and depth == 0:
                        pieces.append(buf)
                        buf = ""
                    else:
                        buf += c
                    k += 1
                if buf:
                    pieces.append(buf)

                for piece in pieces:
                    # Strip character classes [..] and any nested groups.
                    cleaned = re.sub(r"\[[^\]]*\]\??", "", piece)
                    cleaned = re.sub(r"\([^)]*\)\??", "", cleaned)
                    # Strip remaining regex metachars + leading/trailing whitespace.
                    cleaned = re.sub(r"[\\^$.?*+|]", "", cleaned).strip()
                    cleaned = cleaned.lower()
                    cleaned = re.sub(r"[^a-z0-9_-]", "", cleaned)
                    if cleaned and len(cleaned) >= 2:
                        keywords.append(cleaned)
                i = j
                continue
        i += 1

    # Also capture bare \bword\b patterns that aren't in alternation groups.
    for word in re.findall(r"\\b([a-z][a-z0-9_-]+)\\b", pattern.lower()):
        if word not in keywords:
            keywords.append(word)

    return keywords


def _read_v2_skill_metadata(skill_md_path: Path) -> tuple[tuple[str, ...], bool, tuple[str, ...], tuple[str, ...]]:
    """Read v2 sibling files (triggers.yaml, knowledge/) and return data in
    the shape v1 SkillMetadata expects.

    Returns (triggers, always_run, always_run_for_domains, knowledge) where:
      - triggers: flat keyword strings extracted from triggers.yaml's
        prompt_match patterns (plus any explicit flat strings).
      - always_run: True iff triggers.yaml has a rule like '{type: always_on}'
        or '{always_run: true}'.
      - always_run_for_domains: from a special 'always_run_for_domains'
        list in triggers.yaml (rare; default empty).
      - knowledge: filenames in <skill>/knowledge/*.md, preserving case.

    Returns empty tuples / False if any v2 file is missing or malformed.
    The v1 caller treats this as "no triggers / no knowledge" without
    erroring.
    """
    import yaml

    skill_dir = skill_md_path.parent

    triggers: list[str] = []
    always_run = False
    always_run_for_domains: tuple[str, ...] = ()

    triggers_yaml = skill_dir / "triggers.yaml"
    if triggers_yaml.exists():
        try:
            data = yaml.safe_load(triggers_yaml.read_text()) or {}
        except yaml.YAMLError:
            data = {}
        if isinstance(data, dict):
            rules = data.get("rules") or []
            if isinstance(rules, list):
                for rule in rules:
                    if not isinstance(rule, dict):
                        continue
                    rtype = rule.get("type")
                    if rtype == "always_on":
                        always_run = True
                    elif rtype == "prompt_match":
                        pat = rule.get("pattern", "")
                        if isinstance(pat, str):
                            triggers.extend(_extract_keywords_from_pattern(pat))
                    # file_glob / bash_match patterns aren't v1-shaped
                    # triggers; v1 only cared about flat-string set-intersection.
            # Backward-compat: top-level always_run / always_run_for_domains
            # in triggers.yaml take precedence if present.
            if data.get("always_run") is True:
                always_run = True
            ar4d = data.get("always_run_for_domains") or []
            if isinstance(ar4d, list):
                always_run_for_domains = tuple(str(d) for d in ar4d)

    # Knowledge: enumerate sibling knowledge/*.md filenames.
    # Map v2 filenames back to v1 names where applicable, so downstream
    # callers that look up files via crucible.knowledge.loader (which
    # still uses the v1 flat bundled location) find the right content.
    # Files not in the reverse-map pass through under their v2 name.
    knowledge_files: list[str] = []
    knowledge_dir = skill_dir / "knowledge"
    if knowledge_dir.is_dir():
        for child in sorted(knowledge_dir.iterdir()):
            if child.is_file() and child.suffix == ".md":
                v1_name = _V2_KNOWLEDGE_TO_V1.get(child.name, child.name)
                knowledge_files.append(v1_name)

    # Dedupe and preserve order
    seen: set[str] = set()
    unique_triggers: list[str] = []
    for t in triggers:
        if t not in seen:
            seen.add(t)
            unique_triggers.append(t)

    return (
        tuple(unique_triggers),
        always_run,
        always_run_for_domains,
        tuple(knowledge_files),
    )


@lru_cache(maxsize=64)
def _load_skill_cached(skill_name: str, path_str: str) -> tuple[SkillMetadata, str] | str:
    """Internal cached skill loader.

    Returns tuple on success, error string on failure.
    Using path_str as cache key to invalidate on path changes.

    v2 shim: reads triggers + always_run + knowledge from v2 sibling
    files (triggers.yaml, knowledge/) and merges them with whatever
    happens to be in the SKILL.md frontmatter. Lets v1 callers keep
    working against v2-shape content.
    """
    path = Path(path_str)
    content = path.read_text()
    result = parse_skill_frontmatter(content)

    if result.is_err:
        return f"Failed to parse skill '{skill_name}': {result.error}"

    # Read v2 sibling files
    v2_triggers, v2_always_run, v2_ar4d, v2_knowledge = _read_v2_skill_metadata(path)

    # v1 frontmatter wins if present (some skills may still have v1 shape
    # during the transition); fall back to v2 siblings otherwise.
    triggers = result.value.triggers or v2_triggers
    always_run = result.value.always_run or v2_always_run
    always_run_for_domains = result.value.always_run_for_domains or v2_ar4d
    knowledge = result.value.knowledge or v2_knowledge

    metadata = SkillMetadata(
        name=skill_name,
        version=result.value.version,
        triggers=triggers,
        always_run=always_run,
        always_run_for_domains=always_run_for_domains,
        knowledge=knowledge,
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
