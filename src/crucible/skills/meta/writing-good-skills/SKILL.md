---
name: writing-good-skills
description: Author or refactor an agent skill (SKILL.md file) using mid-2026 practitioner consensus. Use when creating a new Crucible skill from scratch, refactoring an existing skill for clarity or token efficiency, reviewing a skill before bundling it, or evaluating whether a SKILL.md file is well-formed. Covers description-as-trigger, body composition, bundling decisions, composition budgets, eval pillars, and the eight common antipatterns. Do NOT use for general prompt writing — skills are a specific packaging format with frontmatter, progressive disclosure, and bundled resources.
version: "2.0"
---

# Writing Good Skills

Principles for authoring effective SKILL.md files. Derived from SkillsBench (arXiv 2602.12670, Feb 2026), the cross-vendor SKILL.md spec (agentskills.io, Dec 2025), MACLA / Mem^p / LEGOMem procedural-memory papers, and practitioner writeups (Simon Willison, macwright, dave.engineer, Tessl).

For the full research synthesis with citations, see `references/research-mid-2026.md`. Load it only when you need to verify a claim or surface evidence — not for routine authoring.

## Six-step authoring process

1. **Understand** — Collect 3+ concrete examples of how the skill will be used. Skip only if usage patterns are obvious.
2. **Plan** — Identify what scripts, references, and assets the skill will need before creating the folder.
3. **Initialize** — Create the Crucible skill folder: `src/crucible/skills/<name>/` (or `src/crucible/skills/meta/<name>/` for behavioral skills), with `SKILL.md`, `triggers.yaml`, and `knowledge/` `assertions/` `checks/` `personas/` `hooks/` subdirs as needed. Mirror an existing skill's structure.
4. **Edit** — Write SKILL.md + bundled resources. Information lives in EITHER SKILL.md OR a references file — never both.
5. **Validate** — Verify the skill discovers and routes: `crucible skills discover <name>` (Tier 1 + Tier 2) and `crucible triggers match --prompt "<a realistic trigger>"`. Then forward-test with a subagent on a realistic task (the subagent should not know it's being tested — pass artifacts, not your diagnosis).
6. **Iterate** — Real usage exposes what was unclear. Update and re-test.

## Principles

### Triggering (the `description` field IS the trigger)

- **Description-as-trigger, not summary.** The `description` field is the *only* text pre-loaded into context for retrieval (in Crucible, it's what `discover_skills` Tier 1 surfaces and what `triggers.yaml` `prompt_match` patterns complement). Write it as "Use when X" instructions in imperative third person — not marketing copy.
- **Include both what + when.** The description MUST describe what the skill does AND specific triggers/contexts. Body-level "When to Use" sections are useless because the body only loads after triggering.
- **Negative tests.** Verify the skill does NOT fire on adjacent-but-wrong prompts. "Irrelevant skill triggered" is as expensive as "skill missed." In Crucible, add a routing test that asserts the skill stays quiet on a near-miss prompt.

### Body / Content

- **Procedural, not conceptual.** Skills carry recipes, conventions, and workflows. They don't explain what things are. Skills add +50pp in pretraining-underrepresented domains (healthcare, crypto, manufacturing) and only ~+5pp in software/math (SkillsBench).
- **Detailed > comprehensive.** Compact (~17pp) and detailed-with-examples (~19pp) both beat exhaustive documentation (−3pp). Past a token threshold, more prose hurts.
- **Absolute verbs.** Replace "should" and "prefer" with "MUST", "Never use v1", etc. Soft directives get ignored under load.
- **Imperative/infinitive form.** Write "Run X" not "You should run X" or "I would run X."
- **Under 500 lines in the body.** Split into `references/` files when approaching this limit.

### Bundling

- **Scripts the model runs > code blocks it re-derives.** Skills win when they tell the agent to *execute* a bundled script, not when they hand it Python to retype. Token-efficient, deterministic, drift-free.
- **Cheap-model viability is the bundling test.** A well-bundled skill lets Haiku/Sonnet succeed where unaugmented Opus fails. If your skill only works with the strongest model, it's underspecified.
- **`references/`** for content the agent loads as needed. **`knowledge/`** (Crucible convention) for domain patterns the review surfaces. **`assets/`** for files the agent uses in output (templates). **`checks/`** for deterministic scripts the agent executes (not reads).

### Composition

- **Hierarchical > flat.** Skills-of-skills with phase controls (continue / skip / repeat / abort) generalize better than flat skill collections (MACLA).
- **2–3 active skills is the sweet spot.** Loading 4+ skills concurrently drops gains from +18.6pp to +5.9pp. Treat the skill allowlist as a budget, not a buffet. Crucible's trigger router activates on match — keep `triggers.yaml` patterns specific so a single prompt doesn't light up half the catalog.
- **Static-compile for non-executing harnesses.** Cursor and Copilot can't do runtime skill discovery. Crucible ships a generated `AGENTS.md` for exactly this — the cross-tool compatibility surface.

### Evals

- **Three pillars: viability, compliance, efficiency.** A skill is good iff it (a) accomplishes the task, (b) obeys its own directives, AND (c) at lower token cost than no-skill at all. Track all three or ship token-bloat.
- **Deterministic checks before LLM-judge.** Regex / AST / exit-code validation first. LLM-as-judge only for prose outputs.
- **Roundtrip checks at handoff boundaries.** Validate memory write→read, subagent handoff packets, retry-success vs true-success. Check transitions as hard as outputs.

## Antipatterns (avoid)

1. **Self-generated skills.** Model-authored skills add −1.3pp. Human curation is load-bearing — the model can't author expertise it doesn't have. (A model-drafted skill MUST get a human-curation pass before bundling.)
2. **Missing or wrong frontmatter.** A SKILL.md without YAML frontmatter is invisible to the loader. Still the #1 file-layout bug in 2026.
3. **Code blocks the agent retypes.** Inline Python in SKILL.md that the model reimplements instead of executes. Ship scripts, not snippets.
4. **Mega-skill / kitchen-sink.** One skill with 6000 words of mixed scope, business rules, and safety constraints. LLMs lose coherence and ignore the buried clauses.
5. **Silent-success retries.** "Step passes after 5 retries" gets logged green; the underlying instability is hidden until production.
6. **Loading >3 skills per turn.** −12pp vs the 2–3 optimum. Tighten the allowlist.
7. **Acknowledged-but-not-invoked.** Some harnesses cite the skill in chain-of-thought without actually loading the body. Test invocation, not citation.
8. **Bundling code execution where harnesses forbid it.** Enterprise sandboxes block scripts; the skill becomes dead weight. Provide a non-script fallback.

## What NOT to include in the skill folder

Per the cross-vendor spec, do not create:

- `README.md`
- `INSTALLATION_GUIDE.md`
- `QUICK_REFERENCE.md`
- `CHANGELOG.md`
- Any auxiliary documentation about the skill itself

The skill folder contains only what the AI agent needs to do the job. Auxiliary context belongs in commit messages, project memory, or external docs.

## Related

- `references/research-mid-2026.md` — full research synthesis with citations.
- `meta/but-for-real` — the skeptical-verification skill; apply it after authoring to prove the skill actually works rather than assuming it does.
