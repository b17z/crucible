# Skill-Writing Research — Mid-2026 Synthesis

Full citations and underlying evidence for the principles in `SKILL.md`. Load this file only when you need to verify a claim, surface evidence to a user, or extend the principles.

## What's new in mid-2026

The SKILL.md format went cross-vendor in Dec 2025 — Anthropic open-sourced the spec at agentskills.io; Codex CLI adopted it, Gemini CLI followed. The interesting shift since: **skills are now a research object, not just a packaging convention.**

- **SkillsBench** (arXiv 2602.12670, Feb 2026) gave the field its first ablation numbers. Model-authored skills add ~zero value (−1.3pp). Human-curated procedural skills add +16.2pp. Returns diminish past ~3 skills per task.
- **Procedural-memory papers** (Mem^p, MACLA, LEGOMem) reframe skills as the distillation half of an agent's long-term memory loop, not static prompts.
- **Distribution** went from `git clone` to plugin marketplaces. Anthropic's official one launched Jan 2026, Superpowers joined Jan 15.
- **The new bar** is the skill-evaluator meta-skill, not the skill-creator. Authoring is solved; knowing whether your skill is good is the open problem.

## Principles (with citations)

### Triggering

- **Description-as-trigger, not summary.** The `description` field is the only thing pre-loaded into context for retrieval — write retrieval text, not marketing copy. Sources: Anthropic best-practices; foojay practitioner writeup.
- **Negative tests in the eval.** Verify the skill *doesn't* fire on adjacent-but-wrong prompts. "Irrelevant skill triggered" is as expensive as "skill missed." Source: Google Cloud evals writeup.

### Body / Content

- **Procedural, not conceptual.** Skills carry +50pp in domains underrepresented in pretraining (healthcare, manufacturing) and ~+5pp in software/math. The value is recipes and conventions, not explanations. Source: SkillsBench.
- **Detailed > comprehensive.** Compact (~17pp gain) and detailed-with-examples (~19pp) both beat exhaustive documentation (−3pp). Past a threshold, more prose hurts. Source: SkillsBench.
- **Absolute verbs.** Replace "should" / "prefer" with "MUST" / "Never use v1". Soft directives get ignored under load. Sources: Google Cloud evals; macwright observed the same in first-run.

### Bundling

- **Prefer scripts the model runs over code blocks it re-derives.** Willison's read of Codex CLI: skills win when they tell the agent to *execute* an existing script and reuse templates, not when they hand it Python to retype. Sources: Willison (simonwillison.net/tags/skills/), Jeremy Daer quote.
- **Cheap-model viability is the bundling test.** A well-bundled skill lets Haiku / Sonnet succeed where unaugmented Opus fails; if your skill only works with the strongest model, it's underspecified. Source: Willison synthesizing Daer.

### Composition

- **Hierarchical, not flat.** MACLA shows meta-procedures (skills-of-skills with continue/skip/repeat/abort controls) provide the largest generalization gain to unseen tasks (−11.9pp without them). Superpowers ships this pattern as phase-skills calling leaf-skills. Sources: MACLA (arXiv 2512.18950); github.com/obra/superpowers.
- **2–3 skills loaded is the sweet spot.** Loading 4+ skills concurrently drops gains from +18.6pp to +5.9pp — composition needs a budget, not unbounded `allowed-skills`. Source: SkillsBench.
- **Static-compile for non-executing harnesses.** `skills-to-agents` compiles SKILL.md → AGENTS.md for Cursor / Copilot which can't do runtime discovery. Assume this fork exists for any cross-tool skill. Source: dave.engineer/blog/2025/11/skills-to-agents/.

### Evals

- **Three pillars: viability, compliance, efficiency.** A skill is good iff it (a) accomplishes the task, (b) obeys its own directives, (c) at lower token cost than no-skill at all. Track all three or ship token-bloat. Sources: Google Cloud evals; SkillsBench harness.
- **Deterministic checks before LLM-judge.** Regex / AST / exit-code validation first. LLM-as-judge only for prose outputs, structured via Pydantic. Source: Google Cloud evals.
- **Roundtrip checks at handoff boundaries.** "Check transitions as hard as outputs" — validate memory write→read, subagent handoff packets, retry-success vs true-success. Source: tessl.io/blog/skills-for-agents-by-an-agent/.

### Distribution

- **Marketplaces beat repos.** Install counts concentrate in the official Anthropic plugin marketplace and SkillsMP. The 277k-install frontend-design skill set the shape: one canonical name, terse description, ships with eval.
- **The open-spec dividend.** SKILL.md portability is now the table-stakes vendor lock-in defense — write to the spec, not to Claude's loader. Sources: Willison; agensi.io/learn/claude-code-skills-vs-cursor-rules-vs-codex-skills.

## Antipatterns (with evidence)

- **Self-generated skills.** Asking the model to write its own skill gives −1.3pp average. The model can't author expertise it doesn't have. Human curation is load-bearing. Source: SkillsBench.
- **Missing / wrong frontmatter.** macwright's first-run skill landed at `.claude/skills/ast-grep.md` with no YAML — invisible to the loader. Still the #1 file-layout bug a year later. Source: macwright.com/2025/10/20/agent-skills.
- **Code blocks the agent retypes.** Inline Python in SKILL.md that the model reimplements instead of executes. Burns tokens, introduces drift. Ship scripts, not snippets.
- **Mega-skill / kitchen-sink.** One skill with 6,000 words of mixed task scope, business rules, and safety constraints. LLMs lose coherence and ignore the buried clauses. Source: digitalapplied (mirrors the 6k-prompt antipattern).
- **Silent-success retries.** A step "passes after 5 retries" gets logged green; underlying instability hidden until prod. Source: Tessl.
- **Bundling arbitrary code execution where harnesses forbid it.** Enterprise sandboxes block scripts; skill becomes dead weight. Source: Google Cloud evals writeup.
- **"Acknowledged-but-not-invoked."** Some harnesses cite the skill in chain-of-thought without actually loading the body. Test invocation, not citation. Source: SkillsBench.
- **Loading >3 skills per turn.** Composition past 3 active skills shows −12pp vs the 2–3 optimum. Treat skill-allowlist as a budget. Source: SkillsBench.

## References

- https://simonwillison.net/tags/skills/
- https://macwright.com/2025/10/20/agent-skills
- https://dave.engineer/blog/2025/11/skills-to-agents/
- https://tessl.io/blog/skills-for-agents-by-an-agent/
- https://github.com/obra/superpowers
- https://arxiv.org/html/2602.12670v1 (SkillsBench)
- https://arxiv.org/html/2512.18950 (MACLA)
- https://arxiv.org/html/2508.06433v2 (Mem^p)
- https://arxiv.org/html/2510.04851v1 (LEGOMem)
- https://medium.com/google-cloud/agent-skills-evals-stop-vibe-testing-your-skills-edd9eaaa6a1a
- https://developers.openai.com/blog/eval-skills
- https://www.agensi.io/learn/claude-code-skills-vs-cursor-rules-vs-codex-skills
- https://foojay.io/today/best-practices-for-working-with-ai-agents-subagents-skills-and-mcp/
- https://github.com/anthropics/skills
