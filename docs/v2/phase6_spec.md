# Phase 6 Spec — Verifier + Parallel Tool Delegation

Design spec (brainstormed 2026-08-08, approved). Implementation plan follows
separately. Ground truth for precision: `docs/v2/phase6_verifier_corpus.md`
(125 known false positives from Phases 0–2 dogfooding).

## Goal

Cut review noise without eating true positives: a deterministic verifier
layer that suppresses known-false-positive finding shapes before display,
an opt-in LLM escalation tier for shapes rules can't decide, and parallel
static-analysis delegation for wall-clock. Handoff success criterion: FP
rate reduced by >50% per review-pass-dollar; this build gates at **125/125
corpus suppression** (every corpus group is rule-decidable, so the
deterministic tier — cost $0 — clears the whole corpus).

## Decisions (from brainstorm)

1. Parallelism covers **tool delegation only** (semgrep/ruff/slither/bandit
   currently run sequentially).
2. The verifier sits in the **shared pipeline** (`review/core.py`) so all
   four surfaces get it: CLI review, MCP `review()`, pre-commit hook,
   PostToolUse/pretool hooks.
3. **Deterministic tier always-on** (escape hatch: `verify: false`);
   **LLM tier off-by-default**, opt-in, review surfaces only — never in
   pre-commit or the coding hooks.
4. Corpus eval is an **enforced pytest** at full 125/125, plus a
   true-positive control group that must never be suppressed.
5. Architecture: **code predicates + cascading YAML bindings** (house
   cascade pattern; projects extend without writing python).

## Components — `src/crucible/verify/`

### `predicates.py`

Pure functions `(finding, file_content) -> bool`; True = confirmed false
positive → suppress. Written in the suppress direction (no invert flags).
Registry: `PREDICATES: dict[str, Callable]`.

| Predicate | Logic | Corpus group |
|---|---|---|
| `is_test_file` | path under `tests/`, or `test_*.py` / `*_test.py` / `conftest.py` | 3 — `bandit/B101` (114) |
| `octal_without_other_write` | parse chmod octal literal at the match; suppress when `o+w` bit absent | 2 — `world-writable-permissions` (1) |
| `is_cli_entry_point` | file imports argparse AND matched line consumes `args.*` (CLI trust model, not HTTP) | 1 — `user-input-in-path` (6) |
| `match_in_string_literal` | match sits inside a string literal, not a comment (`# TODO` comments stay findings) | 5 — `no-todo-without-issue` (3) |
| `subprocess_import_used` | the `subprocess` import is exercised in-file (`run`/`Popen` called); import-level warning is noise when usage exists and usage-level rules still fire | 4 — `bandit/B404` (1) |

### `bindings.py`

Loads `verifiers.yaml` through the standard cascade: `.crucible/verifiers.yaml`
→ `~/.claude/crucible/verifiers.yaml` → bundled (`verify/bundled/verifiers.yaml`).
Entry shape:

```yaml
verifiers:
  - rule: bandit/B101          # tool findings: "<tool>/<rule>"; enforcement findings: assertion id
    predicate: is_test_file
    reason: "assert is pytest's mechanism; test runs never use -O"
disable: []                    # project/user files may disable bundled bindings by rule
```

First-found-wins per rule key, matching the other cascades. Bundled file
ships the five corpus bindings.

### `core.py`

`run_verification(tool_findings, enforcement_findings, repo_root, config)
-> (tool_findings, enforcement_findings, errors)`:

- Index bindings by rule key; findings with no binding pass through untouched.
- Bound findings: read the finding's file (relative to repo_root), evaluate
  the predicate, and on True mark the finding suppressed with
  `suppression_reason = "verifier:<predicate> — <reason>"`.
- Suppression marks, never drops: suppressed findings stay in the result and
  render in the existing "Suppressed" sections, so verifier behavior is
  auditable. They are excluded from severity counts and gate decisions —
  the same contract inline `crucible-ignore` suppressions already have.
- The verifier only suppresses; it never raises severity, never adds
  findings, never touches unbound rules.

### `llm.py` (escalation tier, opt-in)

For findings that survive the deterministic tier when `verify_llm: true`:
batch per file with content context, reuse `compliance.py`'s client and
token-budget plumbing, prompt per the corpus doc's framing — construct the
strongest counterargument to the finding; suppress only if it is materially
stronger than the finding's evidence, with the counterargument recorded as
the suppression reason. Budget-capped; on budget exhaustion or API error,
findings pass through unsuppressed. CLI/MCP review paths only.

## Model change

`ToolFinding` gains `suppressed: bool = False` and
`suppression_reason: str | None = None`, mirroring `EnforcementFinding`.
Set via `dataclasses.replace` (frozen). Display/count paths that already
split suppressed enforcement findings learn the same split for tool
findings.

## Parallel delegation

`run_static_analysis` runs its four delegate calls through
`ThreadPoolExecutor` (subprocess-wait-bound; threads suffice). Results
collect in fixed tool order (semgrep, ruff, slither, bandit) so output
ordering stays deterministic; per-tool errors aggregate into `tool_errors`
exactly as today. Per-tool timeouts unchanged (they live in the delegates).

## Error handling (errors as values, fail-open toward showing findings)

- Predicate raises, or finding's file unreadable/missing → finding passes
  through **unsuppressed**. The verifier must never eat a true positive
  because of its own bug.
- Malformed `verifiers.yaml` → error string in the pipeline's existing
  errors channel; that file's bindings skipped; cascade continues.
- Binding references an unknown predicate → error note, binding skipped.
- LLM tier: API error / budget exhausted → pass through unsuppressed, note
  in errors.

## Config surface

- `verify: false` — kill switch for the deterministic tier (review config
  and precommit/claudecode configs; default true).
- `verify_llm: true` + existing token-budget knobs — LLM tier opt-in
  (review surfaces only; ignored by pre-commit and hooks).
- `.crucible/verifiers.yaml` — project bindings/disables (cascade above).

## Testing & eval

- **Unit**: table-driven per predicate (octal parser and string-literal
  detection get the dense tables); binding cascade resolution (project
  overrides bundled, `disable:` honored, malformed YAML → error + skip).
- **`tests/test_verifier_corpus.py` — the enforced eval**: all 125 corpus
  findings reconstructed as synthetic `ToolFinding`/`EnforcementFinding`
  fixtures with matching file content (hermetic — no semgrep/slither
  needed), fed through `run_verification`. Gate: **125/125 suppressed**.
  Control group of true positives — real `# TODO` comment, chmod `777`,
  `assert` in production code, `eval` in an HTTP handler, unused
  `subprocess` import — must all pass through unsuppressed. Either
  direction failing fails the suite.
- **Parallelism**: delegates stubbed with sleeps; assert wall-clock
  < sum of sequential; assert result order deterministic.
- **LLM tier**: unit tests with a stubbed client (suppress / pass-through /
  budget-exhaustion paths); no live-API tests.

## Non-goals (this phase)

- No parallel skill/persona LLM review passes (revisit later if wanted).
- No verifier-authored assertion refinements — the corpus doc's "refine the
  assertion regexes" punted work stays punted.
- No auto-append of verifier suppressions to the corpus doc (manual per its
  "How to use" section).

## Follow-ups seeded by this phase

- New FP classes found in dogfooding → new predicate + binding + corpus
  entry (the corpus doc grows; the eval gate grows with it).
- mcp 2.0 migration is tracked separately (b17z/crucible#11) and unaffected.
- `compliance.py` LLM response parsing is brittle with current models: during
  this spec's own prewrite review, 3 of 8 responses failed to parse
  (truncation at `max_tokens=1024`; responses not starting with bare JSON).
  Since `verify/llm.py` reuses this plumbing, harden it with structured
  outputs (`output_config.format` guarantees schema-valid JSON) as part of
  that slice.
