# Phase 6 Verifier — known false-positive corpus

This file collects findings from Crucible's own dogfooding that the Phase 6
Verifier should suppress as false positives. The Verifier's success
criterion is "FP rate reduced by >50% per review-pass-dollar"; this is the
ground-truth corpus to measure against.

Each entry: file:line, the assertion that fired, why it's a false positive,
and the strongest counterargument a Verifier could construct against it.

If the Verifier can articulate the same counterargument and assess it as
materially stronger than the finding's evidence, it correctly suppresses
the finding. If it can't, the assertion needs refinement or the Verifier
needs more context.

---

## Corpus from Phase 1a self-review (2026-05-31)

7 findings surfaced by `crucible review` against `cli.py` during the
Phase 1a commit. None caused by Phase 1a's changes; all pre-existing.

### Group 1 — argparse positional args treated as untrusted user input (6 findings)

**Assertion:** `user-input-in-path` (Pattern, severity WARNING).

| Location | Code | Counterargument |
|---|---|---|
| `src/crucible/cli.py:434` | `output_path = Path(args.output)` | This is a CLI write target chosen by the operator at command invocation. The "user input" pattern targets HTTP-handler-style path traversal where the input source is untrusted; a CLI tool's own argparse output is by definition trusted by the operator running it. |
| `src/crucible/cli.py:1384` | `target_path = Path(args.file)` | Same: argparse positional, CLI-time operator-controlled. |
| `src/crucible/cli.py:1820` | `project_path = Path(args.path).resolve()` | `crucible init <path>` — operator picks where to scaffold. |
| `src/crucible/cli.py:1951` | `output_path = Path(args.output)` | CI workflow generator's write target. |
| `src/crucible/cli.py:2211` | `system_dir = Path(args.path) / SYSTEM_DIR if args.path != "." else SYSTEM_DIR` | `crucible system init` — operator-picked project path. |
| `src/crucible/cli.py:2225` | `path = Path(args.path) if args.path else Path(".")` | Same. |

**Generalized counterargument:** files that look like CLI entry points
(import argparse, define a `main()`, use argparse.Namespace as the input
type) should not be evaluated under the web-request threat model. The
assertion needs to distinguish HTTP request handlers from CLI argument
handlers before flagging.

**Verifier task:** for each of these, produce a counterargument that
includes (a) the file is a CLI entry point, (b) the input source is
argparse not HTTP, (c) the operator running the CLI is the trust boundary.
If the counterargument scores stronger than the finding's
generic-path-traversal evidence, suppress.

### Group 2 — chmod 0o755 on an executable hook script (1 finding)

**Assertion:** `world-writable-permissions` (Pattern, severity WARNING).

| Location | Code | Counterargument |
|---|---|---|
| `src/crucible/cli.py:1618` | `hook_path.chmod(0o755)` | 0o755 is **not world-writable** (no `o+w` bit). It's owner-rwx, group-rx, other-rx — exactly the correct permission for an executable shell script that any user on the system should be able to invoke. The assertion's name suggests it's catching `o+w` (writable), but 0o755 grants only `o+x` (executable). |

**Counterargument:** the assertion's regex is matching too broadly — likely
catching any chmod with the `5` digit in the "other" slot, conflating
read+execute (5) with write (which would be 2, 3, 6, or 7). 0o755 is the
canonical permission for an executable file the OS package convention
expects.

**Verifier task:** for chmod-with-literal-octal findings, parse the octal,
check the actual "other" permission bits, and suppress if `o+w` (bit 2) is
absent. This is a deterministic check — a Verifier with file context
should not need an LLM to figure this out.

---

## How to use this corpus

When Phase 6 lands:

1. Run `crucible review src/crucible/cli.py` against this codebase.
2. For each finding in this corpus, check whether the Verifier suppressed
   it.
3. Per-finding suppression rate is a direct measurement of Verifier
   precision.
4. New false positives that surface during normal use get appended here;
   the corpus grows over time.

If Crucible v2.0 ships with no Verifier and these findings still surface,
either suppress them at source with assertion-specific noqa comments or
refine the assertion regexes themselves. Don't ship with known-noise.

## Punted work

- **Refining `user-input-in-path` to scope-detect CLI vs HTTP context.**
  Could be a Phase 6 deliverable or a separate assertion-author pass.
- **Refining `world-writable-permissions` to parse octal literals correctly.**
  Lower-effort than the CLI/HTTP distinction; potentially a Phase 5
  during-coding-hook tightening rather than Verifier-tier work.

## Corpus addition — Phase 2 self-review (2026-06-01)

Running `crucible review --mode branch --base e78c2e5` against the
Phase 0–2 changes surfaced one new false-positive class beyond the
v1 cli.py findings:

### Group 3 — bandit B101 firing on `assert` in tests (114 findings)

**Assertion:** `bandit/B101` (LOW severity).

**Finding shape:**
> Use of assert detected. The enclosed code will be removed when
> compiling to optimised byte code.

**Counterargument:** every B101 hit is inside a `tests/` file. The
warning is correct *in production code* (compile-time `-O` strips
`assert`), but `pytest` uses `assert` as its primary mechanism and
specifically does not run with `-O`. Bandit doesn't know the file is
a test file; the noise is structural.

**Generalized counterargument for the Verifier:**
- The file is under `tests/` or matches `test_*.py` / `*_test.py`.
- The use of `assert` is inside a function whose name starts with
  `test_` or inside a pytest fixture.
- pytest's runtime contract makes `assert` load-bearing here.

If any of those is true, suppress the B101. Otherwise pass through.

**Verifier task:** for B101 findings, check the surrounding context.
File path contains `/tests/` or matches `test_*.py` → trivial
counterargument, suppress. Same in `conftest.py`. The Phase 6
benchmark should show ~114 of these suppressed cleanly.

### Group 4 — bandit B404 on intentional subprocess import (1 finding)

**Assertion:** `bandit/B404` (LOW severity).

**Finding shape:**
> Consider possible security implications associated with the
> subprocess module.

**Counterargument:** the entire purpose of `delegation.py` is to
delegate to external tools (semgrep, ruff, bandit, slither, gitleaks)
via `subprocess`. The import is the feature, not a vulnerability.
This is a module-import-level warning that should be suppressed at
the file level once and forgotten.

**Verifier task:** flag B404 only if `subprocess` is imported in a
file that doesn't go on to call `subprocess.run` / `subprocess.Popen`
through `_validate_path` or equivalent input sanitization. In
`delegation.py`, every `subprocess.run` call is upstream-protected by
`_validate_path`. Suppress.

---

## Phase 2 corpus stats

| Group | Rule | Count | Suppress? |
|---|---|---|---|
| 1 | `user-input-in-path` (cli.py argparse) | 6 | yes |
| 2 | `world-writable-permissions` (0o755 chmod) | 1 | yes |
| 3 | `bandit/B101` (assert in tests) | 114 | yes |
| 4 | `bandit/B404` (subprocess import) | 1 | yes (with sanitization check) |

Total false positives across Phase 0–2 dogfooding: **122**.

The Phase 6 success criterion ("FP rate reduced by >50% per
review-pass-dollar") should target suppressing ≥61 of these as the
floor. Suppressing all 122 would be a >99% reduction on this corpus,
which is the right ambition given that none of them require deep
reasoning — they're all surface-pattern false positives.
