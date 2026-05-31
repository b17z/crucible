# skills_core/ — Public API SPEC

> **Status:** Phase 0 draft, May 21 2026. Author review pass #1 + SAGE_SKILL_LOADING.md cross-check applied. Ready for Phase 1a green-light.
> **Long-term home:** `src/crucible/skills_core/SPEC.md` (moved there in Phase 1a).
> **Audience:** v2.0 implementers; future Sage migration in v2.x.

## Resolved decisions log

These supplement the handoff doc's Part 9 with v2.0-implementation-level decisions.

- **R1.** Subpackage destinations approved as recommended. Both `crucible.core.models` and `crucible.core.enforcement.models` coexist; no preemptive rename unless an import-site ambiguity surfaces during Phase 2.
- **R2.** Persona folder names follow the repo's existing `-engineer` suffix convention. SPEC and Phase 1b use `uiux-engineer`, `accessibility-engineer`, `web3-engineer`, `backend-engineer`, etc. The handoff doc's clipped names are not reflected in code.
- **R3.** Dual-path resolver scoped to 3 shape-changing rows: knowledge, assertions, prewrite. Skills shape-stable; ignore outlier excluded.
- **R4.** Prewrite migration is structural: `crucible migrate v1-to-v2` reads `prd.md`, creates `pre-write/prd/` folder, synthesizes `SKILL.md` with the prewrite body as content. **Idempotency is a hard requirement** — second run is a no-op. Migrate command scope excludes the package's own bundled `templates/prewrite/` (only operates on `.crucible/` project overrides).
- **R5.** `crucible.errors` extraction decision deferred to v2.x. The seam is documented below; no `crucible-common` lib in v2.0.
- **R6.** `enforcement/budget.py` is LLM-assertion-specific (not a general cost tracker). Lands at `core/enforcement/budget.py`. A separate cost module for the Phase 6 verifier loop gets created independently when needed.
- **R7.** `domain/detection.py` collapses to `core/detection.py`. The `domain/` subfolder is dropped — one file doesn't justify it.
- **R8.** SAGE cross-check applied. `skills_core/` is loader primitives only: cascade resolution + SKILL.md parsing + types. Progressive disclosure (`discover_skills` / `activate_skill` / `load_knowledge`), trigger routing, and concrete `*_SPEC` constants all move to Crucible's `core/`. Rationale: Sage's research-skill API is eager-by-design and Sage's `triggers:` frontmatter is dead code being deprecated in favor of `description`-routing — building Crucible's tier model and trigger schema into `skills_core/` would impose Crucible-specific shapes on a library that needs to serve both consumers. The right boundary is "what a skill is on disk" (in skills_core) vs. "what each consumer does with it" (in core/).

## Purpose

`skills_core/` is the internal module that owns the **loader primitives**
for Crucible v2.0: cascade resolution, SKILL.md parsing, and the shared
types those primitives produce. It is *not* a separately released PyPI
package in v2.0; extraction to `crucible-skills-core` is deferred to
v2.x when Sage migrates.

It is deliberately **narrower** than the first SPEC draft. Progressive
disclosure (tier 1/2/3 loading), trigger routing, and concrete
`SKILLS_SPEC`/`KNOWLEDGE_SPEC`/`ASSERTIONS_SPEC` constants live in
Crucible's `core/`, not here. See "Why this shape" below.

The point of this SPEC is to define the **public API surface** so that:
1. Code outside `skills_core/` imports only from `crucible.skills_core`
   (never `crucible.skills_core._loader` or other private submodules).
2. When Sage eventually consumes this, the extraction is a packaging
   move — not an API redesign.

### Why this shape (cross-check with SAGE_SKILL_LOADING.md)

The SAGE cross-check surfaced three structural differences between
Sage's existing skill model and the assumptions the first SPEC draft
was making:

- **Sage's research-skill loader is eager and single-tier.** It calls
  `Skill.content + sorted(docs/*.md) + shared_memory` and concatenates
  everything into one prompt. There is no "load body separately from
  frontmatter" tier. Putting `discover_skills()` / `activate_skill()`
  in `skills_core/` would force Sage's loader to either become
  progressive (a rewrite Sage doesn't want) or live around the API
  rather than through it.
- **Sage's `triggers:` frontmatter field is dead code being deprecated
  in favor of `description`-based routing.** Crucible's `triggers.yaml`
  is a Crucible-specific schema (regex/glob patterns + event types).
  These two things share a name accidentally. A typed `triggers` field
  in the loader API would encode Crucible's schema into a library that
  Sage explicitly doesn't want it in.
- **Sage's default-skill set is unstable.** The `sage-memory` skill is
  going to be obsoleted when server-side background checkpoint dispatch
  lands. Anything in `skills_core/` that depended on knowing what
  default skills exist or how many there are would be brittle from day
  one.

The fix: `skills_core/` exposes loader primitives — *what a skill is on
disk* — and stops there. Each consumer (Crucible's progressive disclosure
in `core/`, Sage's eager `build_context()` in Sage) implements its own
loading strategy on top of those primitives. The progressive-disclosure
flow is still a v2.0 deliverable; it just doesn't live in `skills_core/`.

## Module layout

```
src/crucible/skills_core/
├── __init__.py                  # Public surface — re-exports only, __all__ enforced
├── _types.py                    # Internal: CascadeSpec, ResolvedPath, RawSkill
├── _cascade.py                  # Internal: resolve(), list_available()
└── _loader.py                   # Internal: parse_frontmatter(), read_skill()
```

Internal submodules use the `_` prefix. Public access is via
`crucible.skills_core.<name>`. Standard Python conventions enforce this —
no custom lint plugin needed.

The `_progressive_disclosure.py` and `_trigger_router.py` modules
from the v0 draft are **not in `skills_core/`** per R8 — they live in
`src/crucible/core/disclosure.py` and `src/crucible/core/trigger_router.py`
as Crucible-specific orchestration on top of the loader primitives.

## Cascade resolution

All v1 path-search resolvers (skills, knowledge, assertions, prewrite)
shared an identical `project > user > bundled` first-found-wins shape.
v2 consolidates them into one primitive with content-type adapters
as data, not code.

### Phase 0 cascade-surface audit

Five resolvers exist in v1; four follow the cascade pattern, one
(`.crucibleignore`) merges across tiers and stays in `core/ignore.py`.

| Content type | v1 project path | v1 user path | v1 bundled path | v2 path | Shape-stable? |
|---|---|---|---|---|---|
| Skills | `.crucible/skills/<name>/` | `~/.claude/crucible/skills/<name>/` | `<pkg>/skills/<name>/` | unchanged | YES |
| Knowledge | `.crucible/knowledge/<file>.md` | `~/.claude/crucible/knowledge/<file>.md` | `<pkg>/knowledge/principles/<file>.md` | `.crucible/skills/<persona>/knowledge/<file>.md` | NO |
| Assertions | `.crucible/assertions/<file>.yaml` | `~/.claude/crucible/assertions/<file>.yaml` | `<pkg>/enforcement/bundled/<file>.yaml` | `.crucible/skills/<persona>/assertions/<file>.yaml` | NO |
| Prewrite | `.crucible/templates/prewrite/<name>.md` | `~/.claude/crucible/templates/prewrite/<name>.md` | `<pkg>/templates/prewrite/<name>.md` | `skills/pre-write/<name>/` (folder!) | NO (structural) |
| .crucibleignore | `.crucible/.crucibleignore` | `~/.claude/crucible/.crucibleignore` | (none) | unchanged | YES (outlier) |

Three rows are shape-changing: **knowledge, assertions, prewrite** — these
get the dual-path resolver fallback in Phase 2. Skills and ignore stay
shape-stable. User-tier paths stay v1-shape across all rows; only
project-tier paths get fallback support.

**Prewrite is structurally different from knowledge/assertions:** the
former is "single file → skill folder," the latter is "flat → nested
under persona." Phase 2's `crucible migrate v1-to-v2` command handles
the structural reshape; the dual-path resolver handles the lookup
fallback.

**Migration scope guardrails (per R4):**

- Migrate touches `.crucible/` only — never the package's own bundled
  `templates/prewrite/` directory. Bundled content migrates via the
  Phase 2 source-tree refactor, not the runtime migrate command.
- Idempotency is a hard requirement: running `crucible migrate v1-to-v2`
  twice must produce the same end-state as running it once. Test:
  invoke twice on a fixture project, assert second run is a no-op and
  no `.crucible.v1-backup/` files are duplicated, doubled, or
  overwritten.
- Each shape-changing row gets its own migration step. Prewrite's step
  is non-trivial: read `prd.md` content, create `pre-write/prd/` folder,
  synthesize a `SKILL.md` (frontmatter derived from the template's
  intended use; body = original markdown). Knowledge and assertion
  steps are pure file moves into per-persona subdirectories, gated on
  the Phase 2 setup mapping (which persona owns which file).

### Public API — cascade

```python
# crucible.skills_core (re-exported from __init__.py)

@dataclass(frozen=True)
class CascadeSpec:
    """Declarative description of a content type's resolution surface."""
    project_dir: Path
    user_dir: Path
    bundled_dir: Path
    is_folder: bool                  # True = lookup unit is folder; False = file
    suffix: str | None               # e.g., ".yaml" for assertions; None for folders

    # v1→v2 dual-path fallback (None if shape-stable):
    fallback_project_dir: Path | None = None
    fallback_label: str | None = None   # for deprecation warning text


@dataclass(frozen=True)
class ResolvedPath:
    path: Path
    source: Literal["project", "user", "bundled"]
    used_fallback: bool                 # True if v1 path was used; triggers warning


def resolve(spec: CascadeSpec, name: str) -> Result[ResolvedPath, str]:
    """First-found-wins across project → user → bundled.
    If project path miss AND spec.fallback_project_dir is set, try
    fallback before user/bundled and mark used_fallback=True."""


def list_available(spec: CascadeSpec) -> set[str]:
    """All available names across tiers, for discovery."""


# Concrete *_SPEC constants do NOT live here — see core/specs.py.
# skills_core/ exports the CascadeSpec type; Crucible's core/ constructs
# its instances. This keeps skills_core/ free of Crucible-specific paths
# (e.g., the bundled-package root) which would change meaning at v2.x
# extraction time.
```

**Deprecation warnings:** when `used_fallback=True`, callers SHOULD emit
a one-time-per-name warning citing `fallback_label`. The warning text is
data in the spec, not hardcoded in callers — so v2.2 removal is a
one-line change per spec.

The concrete `SKILLS_SPEC`, `KNOWLEDGE_SPEC`, and `ASSERTIONS_SPEC`
instances live in `src/crucible/core/specs.py` and are constructed at
import time from the bundled-package root. Sage in v2.x will construct
its own `CascadeSpec` instances rather than importing Crucible's.
No `PREWRITE_SPEC` — prewrite v2 templates ARE skill folders under
`skills/pre-write/`, so `SKILLS_SPEC` with a subdirectory filter covers it.

## SKILL.md loader

```python
# crucible.skills_core (re-exported)

@dataclass(frozen=True)
class RawSkill:
    """A skill as it exists on disk. Loader output; consumer-agnostic.

    No typed frontmatter fields — `frontmatter` is an open dict and each
    consumer reads the keys it cares about. Sage's research-skill code
    reads `description`; Crucible reads `name`, `description`, and its
    own conventions; future consumers can add fields without changing
    this type.
    """
    path: Path                          # Resolved skill folder
    source: Literal["project", "user", "bundled"]
    used_fallback: bool                 # True if the v1 dual-path fallback was used
    frontmatter: dict[str, Any]         # parsed YAML; open schema
    body: str                           # SKILL.md content after the closing `---`
    sibling_paths: dict[str, Path]      # subfolders/files in the skill dir
                                        # (e.g., {"knowledge": Path(...), "assertions": Path(...)})


def parse_frontmatter(content: str) -> Result[tuple[dict[str, Any], str], str]:
    """Split a SKILL.md string into (frontmatter_dict, body).
    Returns err if no frontmatter delimiters or invalid YAML."""


def read_skill(path: Path, source: str = "project") -> Result[RawSkill, str]:
    """Read a skill folder from disk. Reads SKILL.md, parses frontmatter,
    enumerates sibling subdirectories. Does NOT read knowledge/ or
    assertions/ file contents — callers do that lazily.

    `path` is the resolved skill folder (typically from resolve()).
    `source` is the tier tag from cascade resolution; passed through to
    the returned RawSkill."""
```

That's the entire loader surface. Two functions, one dataclass. Each
consumer wraps this with its own orchestration:

- Crucible's `core/disclosure.py` implements progressive disclosure
  (frontmatter scan at SessionStart → body load on activation →
  per-knowledge-file read on Tier 3).
- Sage's `build_context()` implements eager loading (read_skill →
  concatenate body + every sibling doc + shared_memory substitution).

Both build *on top of* the same primitives. Neither has to fight the
loader's shape.

**No typed frontmatter schema in `skills_core/`.** SKILL.md frontmatter
is an open YAML dict. Crucible's expected keys (`name`, `description`,
optional `version`, etc.) are documented in `templates/CLAUDE.md` and
validated by Crucible-side code in `core/skill_validation.py` — not by
skills_core. Sage's expected keys (`name`, `description`, `author`,
`version`, `tags`, `sage_managed`) are validated by Sage. The loader
exposes whatever was in the YAML; the consumer decides what's required.

The v1 `SkillMetadata` and `KnowledgeMetadata` dataclasses become
Crucible-side validation types in `core/skill_validation.py`. They are
not part of the skills_core public API.

## What stays out of skills_core/

These exist in v1 (or are planned for v2) and have to live somewhere,
but **not** in `skills_core/`:

- **Progressive disclosure orchestration** (`discover_skills` /
  `activate_skill` / `load_knowledge`) — Crucible-specific tiered
  loading. Lives in `core/disclosure.py`. Built on `read_skill()`.
- **Trigger routing** — Crucible's `triggers.yaml` parsing + regex/glob
  matching + event-shape matching. Lives in `core/trigger_router.py`.
  Crucible's `triggers.yaml` is a *separate file inside each skill
  folder*, not a frontmatter field; the loader exposes it via
  `RawSkill.sibling_paths["triggers.yaml"]` if present, and
  `core/trigger_router.py` reads it.
- **Concrete `*_SPEC` constants** (`SKILLS_SPEC`, `KNOWLEDGE_SPEC`,
  `ASSERTIONS_SPEC`) — encode Crucible's bundled-package layout. Live
  in `core/specs.py`. `skills_core/` exports the `CascadeSpec` type;
  Crucible constructs the instances.
- **Frontmatter schema validation** — Crucible-side expected-key
  checking lives in `core/skill_validation.py`. The loader returns
  whatever YAML was in the file.
- **`.crucibleignore` resolution** — different semantics (merges across
  tiers, doesn't pick one). Stays in `core/ignore.py`.
- **Enforcement runtime** (assertion *execution*, pattern matching,
  compliance) — `skills_core/` discovers and loads them; running them is
  enforcement-specific logic that belongs in `core/enforcement/`.
- **Persona/voice rendering** — how a finding gets rendered with the
  adversarial vs. default voice is review-pipeline concern, not skills_core.
- **Tool wrappers** (semgrep, ruff, bandit, slither) — `core/tools/`.
- **Verifier loop, parallel orchestrator** — `core/verifier.py`,
  `core/parallel_orchestrator.py`. They consume skills via `skills_core`
  but don't belong inside it.

The dividing line: anything that's about *what a skill is on disk and
how to find one* is in `skills_core/`. Anything about *what each
consumer does with a loaded skill* is outside. Per the SAGE cross-check,
the consumer's loading strategy (progressive vs. eager), trigger model
(file-driven vs. description-driven), and validation schema are all
*consumer-side concerns* — `skills_core/` doesn't pick a winner.

## Compatibility with future Sage extraction

When Sage migrates in v2.x:

1. Move `skills_core/` to its own repo, rename package to
   `crucible_skills_core`.
2. Publish as `crucible-skills-core==0.1.0` on PyPI (name reserved per
   Layer 4 of Part 5).
3. Both Crucible and Sage depend on it, pinned to exact version.
4. The public API in this SPEC becomes the v0.1.0 API.

What this means for v2.0 design choices:

- **No Crucible-specific assumptions in the public types.** `CascadeSpec`,
  `ResolvedPath`, `RawSkill` — none of these reference Crucible's domain
  model, enforcement, review pipeline, or expected frontmatter keys.
  They describe skills as a generic concept.
- **No I/O coupling.** The cascade resolver returns `Path` objects;
  the caller decides what to read. `read_skill()` reads the skill folder
  but does not eagerly fetch sibling content. Sage's eager `build_context()`
  can layer on top by enumerating `sibling_paths` and reading each;
  Crucible's progressive disclosure can defer those reads.
- **Result types are `Result[T, str]`** (from `crucible.errors`). This
  is a known extraction seam — see "Known extraction seams" below.
- **Open frontmatter schema.** Per the SAGE cross-check, putting typed
  frontmatter fields in the public API (like a `triggers: tuple[str, ...]`
  in v0's `SkillSummary`) would have imposed Crucible-specific shapes on
  a library Sage explicitly doesn't want them in. `RawSkill.frontmatter`
  is a `dict[str, Any]`; each consumer validates its own keys.

**SAGE cross-check status:** done. `SAGE_SKILL_LOADING.md` v1 reviewed
against this SPEC. The three weighted findings (loader-not-discovery,
`triggers:` is dead, default-skill set unstable) are reflected in the
shape of `RawSkill`, the open-frontmatter decision, and the explicit
"no enumeration of Sage's defaults anywhere in this SPEC" stance.

## Known extraction seams (decide at v2.x, not v2.0)

When `skills_core/` becomes `crucible-skills-core` PyPI, these are the
points where a decision has to be made. They are **not** v2.0 problems;
the SPEC documents them so future-us doesn't rediscover the question.

1. **`crucible.errors` (`Result[T, str]`).** Three options at extraction:
   (a) inline a copy into `crucible-skills-core`, (b) ship a minimal
   `crucible-common` lib both packages depend on, (c) make `skills_core`'s
   public API return tuples/exceptions instead of `Result`. Choose at
   extraction time based on the actual import surface — if only ~3
   `Result` call sites cross the boundary, (a) is cheapest; if it's the
   dominant return type, (b) becomes worthwhile; (c) only if `Result`
   turns out to be a Crucible-only idiom Sage doesn't want.
2. **Path-handling for the `<pkg>` root.** `CascadeSpec.bundled_dir` is
   computed at construction time relative to a package root. When
   extracted, "the package root" changes meaning. Either the specs
   become factory functions parameterized by package root, or the
   extracted lib assumes each consumer constructs its own specs. Defer.
3. **Logging / deprecation-warning surface.** v2.0 uses `warnings.warn`
   for cascade-fallback deprecation. When extracted, the warning's
   "package" attribution changes. Trivial to fix; flagging for
   completeness.

## Known design decisions to revisit

1. **`PREWRITE_SPEC` dropped in favor of `SKILLS_SPEC` with subdir
   filter.** Cleaner, but if v2.x adds a non-skill content type that
   currently behaves like prewrite, this might need to come back. (This
   is a `core/specs.py` decision, not a `skills_core/` decision — the
   type-vs-instance split per R8 means revisiting it doesn't touch
   `skills_core/` at all.)
2. **Trigger routing moved out of `skills_core/` to `core/trigger_router.py`.**
   v0 draft had this in `skills_core/`; the SAGE cross-check found that
   Sage's `triggers:` frontmatter is dead code and Sage's planned routing
   is `description`-based, so Crucible's `triggers.yaml` schema doesn't
   belong in a shared loader library. Revisit only if a future second
   consumer turns out to need the same trigger schema Crucible uses.
3. **`RawSkill.sibling_paths` is a `dict[str, Path]`, not deeper structure.**
   The loader enumerates immediate children of the skill folder but
   doesn't recurse or read content. Consumers that need per-file
   metadata (like Crucible's `KnowledgeMetadata` from v1) read the files
   themselves and parse. Revisit if multiple consumers all reimplement
   the same per-knowledge-file parsing.
4. **No async surface.** Cascade resolution is fast (filesystem only);
   parallel persona invocation is not a `skills_core/` concern. If a
   future tier 3 fetches from network, this changes.

## Out of scope for this SPEC

- The implementation of each `_module.py`. SPEC is the public surface;
  internals are an implementation detail of Phase 3+.
- The `migrate v1-to-v2` command — it's a CLI surface, not a
  `skills_core/` API.
- Hook dispatcher, verifier, parallel orchestrator — all `core/`, not
  `skills_core/`.
- Configuration loading (`.crucible/config.toml`) — `core/config.py`.

---

*End of SPEC v1. Author review pass #1 and SAGE_SKILL_LOADING.md
cross-check both applied. Ready for Phase 1a green-light.*
