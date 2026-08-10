# Spec — Prewrite Checklist Mode (no-API semantic review + honest exit codes)

Version: 1.0 (2026-08-10). Approved via brainstorm. v2.1 track.

## Goal

Make `crucible prewrite review` usable without the Anthropic API:
`--checklist` renders the semantic assertions as a structured
evaluation package for the calling agent (any model) to work through
inline. Fix the exit-0-when-nothing-ran bug in the same stroke: a
keyless run that evaluates zero assertions must not report "passed".

## Decisions (from brainstorm)

1. Agent-mediated tier ships now: the harness model evaluates the
   assertions; crucible provides the structure and the record.
2. Gateway base-URL support (Anthropic-compatible proxies) is filed
   as an issue, not built here.
3. Honest exits: all-assertions-errored → exit 1 with a `--checklist`
   pointer; partial errors → prominent warning, findings-based exit
   unchanged (a budget-exhausted partial run stays a pass if its
   evaluated findings pass).

## 1. CLI surface — `cmd_prewrite_review` (`src/crucible/cli.py`)

- New flag `--checklist`: skip the API entirely. Render the
  evaluation package (section 2) for exactly the assertions the API
  path would have run (same template detection, same skill
  filtering — the selection logic must be shared, not duplicated).
  Exit 0 on successful render (rendering is not a verdict). Must not
  require the `anthropic` package or any key.
- `--checklist --json`: emit the same package as JSON — `{"path",
  "template", "mode": "checklist", "checks": [{"id", "severity",
  "criteria"}]}`.
- **Exit-code fix (API path)**: after a run, if `result.errors` is
  non-empty AND zero assertions produced a verdict (all errored —
  key missing, package missing, API down), print the errors plus one
  pointer line — run with `--checklist` to evaluate with the agent
  you already have — and exit 1. `--fail-on` does not override this:
  nothing was evaluated.
- **Partial errors**: some assertions evaluated, some errored →
  print a prominent warning line (`⚠ N of M assertions errored —
  partial evaluation`) before the verdict; exit stays findings-based.
- Unchanged: full evaluation pass/fail exits, `--fail-on` semantics,
  existing JSON output for API runs (gains an `"evaluated"` count
  alongside `"errors"`).

## 2. Checklist output format (binding)

```
# Pre-Write Review Checklist

Spec: <path> (template: <detected-or-given template>)

Evaluate the document against each check below. For each, report
PASS or FAIL with one line of evidence (a quote or section
reference). A FAIL on any error-severity check means the spec is
not ready. Record the completed checklist next to the spec (in the
workbench, if you keep one).

## Checks

### <assertion_id> — severity: <severity>

<the assertion's compliance criteria text, verbatim>
```

One `###` block per assertion, in the order the API path would run
them. No other prose.

## 3. Implementation shape (`src/crucible/prewrite/review.py`)

- Factor assertion selection (template detect → load → filter to
  LLM/prewrite assertions with their id/severity/criteria) out of
  `prewrite_review` into a function both paths call, returning the
  ordered check list. `prewrite_review`'s behavior is unchanged for
  the API path.
- New `render_prewrite_checklist(...)` producing section 2's format
  (and a structure the JSON branch can serialize). Pure function, no
  network, errors as values.

## 4. Docs and wiring

- `meta/delivery-loop` SKILL.md step 3: the no-key fallback sentence
  now names the real command — run
  `crucible prewrite review <spec-path> --checklist`, evaluate every
  check inline, record the completed checklist in the workbench; a
  FAIL on an error-severity check blocks step 5 the same as a failed
  API run.
- `docs/PORTABILITY.md` Models section: one added line — without a
  key, `--checklist` turns prewrite review into an agent-evaluated
  gate; no Anthropic dependency.
- `docs/BUILD-ALONG.md` kickoff prompt step 4: one added sentence —
  if the output shows key-not-found errors, rerun with
  `--checklist` and evaluate the checks yourself, showing me the
  results.
- `docs/FEATURES.md` prewrite section documents the flag.

## Acceptance criteria

1. `--checklist` on a real spec renders every applicable assertion
   id with its criteria, exits 0, and completes with no `anthropic`
   import and no key in the environment (test guards both).
2. Keyless API run (env key absent, config-key loader patched to
   None): exits 1, output contains the `--checklist` pointer;
   `--fail-on info` still exits 1 (nothing evaluated).
3. Partial-error run (one assertion errors, one evaluates clean):
   warning line present, exit reflects findings only.
4. Full-evaluation pass and fail exits unchanged (existing tests
   stay green); `--checklist --json` shape as specified.
5. Docs: delivery-loop step 3 names `--checklist` (content
   assertion); PORTABILITY + BUILD-ALONG kickoff + FEATURES updated;
   every printed command runs (checklist command exit 0 live).
6. Full suite green at 927 baseline + new tests; ruff clean; wheel
   unaffected (no new package files beyond code).

## Non-goals

- No gateway/base-URL support (issue). No checklist analog for
  `crucible review --llm`/`--verify-llm` (issue if wanted). No
  change to `PrewriteResult.passed` semantics — honesty lives in
  the exit-code layer. No new config keys.
