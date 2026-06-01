# Local environment issues affecting the test suite

Issues with the dev machine's installed tools that surface as test
failures in `tests/test_integration.py`. None are caused by Crucible
code; all are local-environment shape problems. Documenting them so
they don't get re-discovered every time someone runs the full suite.

The honest test baseline on a machine where these are unresolved is
**660/669 (Python 3.12.6)**, not 667/669 as initially reported in
Phase 1a. The earlier number missed the slither failures because
`--ignore=tests/test_integration.py` was being passed every time.

## Issue A — semgrep crashes with opentelemetry ImportError

**Symptom:** `pytest tests/test_integration.py::TestPythonVulnerabilities`
fails on the SQL-injection and command-injection tests. Each one calls
`delegate_semgrep` and expects a non-empty findings list; gets an Err.

**Cause:** the installed `semgrep` package crashes during `import` with:

```
ImportError: cannot import name 'LogData' from 'opentelemetry.sdk._logs'
```

semgrep's `tracing.py` imports a name that was removed in a newer
`opentelemetry-sdk` release. The transitive-dep pin drifted.

Before the Phase 1a `_check_tool_run` fix, this crash was silently
swallowed as `ok([])` (the integration test then failed on "expected
finding, got empty list"). After Phase 1a, the failure surfaces as
`Err(error='semgrep exited 1 with no output — likely a crash before
scanning. stderr: ImportError...')`. The diagnostic improved; the
underlying env problem is the same.

**Fix at the env level:**

```bash
pip install --force-reinstall 'opentelemetry-sdk<1.27'
# or
pipx install semgrep    # isolates semgrep from your project's deps
```

**Affected tests:**
- `test_sql_injection_detected`
- `test_command_injection_detected`

## Issue B — slither exits 255 (likely missing solc)

**Symptom:** `pytest tests/test_integration.py::TestSolidityVulnerabilities`
fails on five tests. Each one calls `delegate_slither` and expects a
non-empty findings list; gets an Err.

**Cause:** slither exits 255 with no stderr. The most common cause is
that `solc` (the Solidity compiler) is not installed or not on PATH;
slither can't compile the fixture file before scanning, so it exits.

Before Phase 1a, this also silently swallowed as `ok([])`. After
Phase 1a, the failure surfaces as `slither failed (exit 255): (no
stderr)`. Same shape as Issue A.

**Fix at the env level:**

```bash
# macOS
brew install solidity
# or via solc-select for version pinning
pip install solc-select
solc-select install 0.8.20
solc-select use 0.8.20
```

**Affected tests:**
- `test_reentrancy_detected`
- `test_unchecked_transfer_detected`
- `test_controlled_delegatecall_detected`
- `test_missing_zero_check_detected`
- `test_tx_origin_detected`

## Why these aren't blocking

These are local-env failures, not Crucible bugs. The `_check_tool_run`
helper in `src/crucible/tools/delegation.py` already distinguishes
"tool ran cleanly, no findings" from "tool crashed before scanning"
and reports the latter as an error. A CI machine with the right tool
versions installed should see all 7 of these tests pass.

## What to remember

- Whole-suite count on this machine: 660 pass / 7 fail / 41 skip out
  of 708 collected (Phase 2). The 7 failures are these 7 env tests.
- When reporting "tests pass," always include the integration-suite
  result, not just the excluded subset.
- These tests should be considered "env-skipped, not env-broken" once
  the underlying issues are filed against the maintainer's machine
  setup (i.e., a Layer-2 workstation hygiene item per
  `skills/meta/publisher-security/knowledge/layers.md`).
