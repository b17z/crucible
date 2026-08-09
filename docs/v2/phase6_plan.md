# Phase 6 Implementation Plan — Verifier + Parallel Tool Delegation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A deterministic verifier that suppresses known-false-positive findings (gated at 125/125 on the corpus), an opt-in LLM escalation tier, and parallel static-analysis delegation.

**Architecture:** New `src/crucible/verify/` package — pure predicate functions, cascading YAML bindings (rule → predicate), and a `run_verification` pass that marks findings suppressed (never drops them). Wired into all four finding surfaces after dedup, before counts/gates. Spec: `docs/v2/phase6_spec.md`.

**Tech Stack:** Python 3.11+, PyYAML, pytest, anthropic SDK (LLM tier only).

## Global Constraints

- Errors as values (`crucible.errors.Result` where a single fallible value is returned; error-string lists for pipeline channels — match the file you touch).
- Frozen dataclasses for domain types; mutate via `dataclasses.replace`.
- The verifier only ever *marks* `suppressed=True` — it never removes findings, never changes severity, never touches findings whose rule has no binding, and never un-suppresses.
- Fail open toward showing findings: any verifier-internal error (unreadable file, predicate exception, bad YAML) leaves findings unsuppressed.
- Commit style: `type: subject` (no parens, no scope), terse 3–5-line body, no Co-Authored-By trailer.
- `ruff check src/` clean; full suite green (`python -m pytest -q --ignore=tests/test_integration.py`; the 7 `test_integration.py` failures are known-env-broken).
- Never `git add` `.crucible/assertions/test-llm.yaml` or `CRUCIBLE_RESEARCH.md` — they are not ours. Stage files explicitly; never `git add -A`.
- The pre-commit hook dogfoods crucible: fixture strings containing `eval(`/`shell=True`/`TODO` need inline `# crucible-ignore: <rule> -- reason` suppressions on the same line.
- Tests never reach the live Anthropic API (`tests/conftest.py` guard is autouse; LLM-tier tests mock `_get_anthropic_client`).

---

### Task 1: ToolFinding suppression fields

**Files:**
- Modify: `src/crucible/models.py:28-36` (class `ToolFinding`)
- Test: `tests/test_tools.py` (append)

**Interfaces:**
- Produces: `ToolFinding.suppressed: bool = False`, `ToolFinding.suppression_reason: str | None = None`. Later tasks set them via `dataclasses.replace(finding, suppressed=True, suppression_reason=...)`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_tools.py`:

```python
class TestToolFindingSuppression:
    def test_defaults_unsuppressed(self) -> None:
        from crucible.models import Severity, ToolFinding

        f = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="assert used", location="tests/test_x.py:3")
        assert f.suppressed is False
        assert f.suppression_reason is None

    def test_replace_marks_suppressed(self) -> None:
        import dataclasses

        from crucible.models import Severity, ToolFinding

        f = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="assert used", location="tests/test_x.py:3")
        marked = dataclasses.replace(f, suppressed=True,
                                     suppression_reason="verifier:is_test_file — pytest asserts")
        assert marked.suppressed is True
        assert "is_test_file" in marked.suppression_reason
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_tools.py -q` → FAIL (`unexpected keyword`/`no attribute 'suppressed'`).
- [ ] **Step 3: Implement** — in `src/crucible/models.py`, add two fields at the end of `ToolFinding` (after `suggestion`):

```python
    suggestion: str | None = None
    suppressed: bool = False
    suppression_reason: str | None = None
```

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_tools.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add src/crucible/models.py tests/test_tools.py && git commit -m "feat: ToolFinding gains suppression fields"`

---

### Task 2: Predicates

**Files:**
- Create: `src/crucible/verify/__init__.py` (empty for now; populated in Task 4)
- Create: `src/crucible/verify/predicates.py`
- Test: `tests/test_verify_predicates.py`

**Interfaces:**
- Produces:
  - `FindingContext` frozen dataclass: `path: str`, `line: int | None`, `column: int | None`, `match_text: str | None`.
  - Five predicates, each `(ctx: FindingContext, content: str) -> bool`, True = confirmed false positive: `is_test_file`, `octal_without_other_write`, `is_cli_entry_point`, `match_in_string_literal`, `subprocess_import_used`.
  - `PREDICATES: dict[str, Callable[[FindingContext, str], bool]]` mapping each name to its function.

- [ ] **Step 1: Write the failing tests** — create `tests/test_verify_predicates.py`:

```python
"""Table-driven tests for the Phase 6 verifier predicates."""

import pytest

from crucible.verify.predicates import (
    PREDICATES,
    FindingContext,
    is_cli_entry_point,
    is_test_file,
    match_in_string_literal,
    octal_without_other_write,
    subprocess_import_used,
)


def _ctx(path="src/app.py", line=1, column=1, match_text=None):
    return FindingContext(path=path, line=line, column=column, match_text=match_text)


class TestIsTestFile:
    @pytest.mark.parametrize("path,expected", [
        ("tests/test_enforcement.py", True),
        ("pkg/tests/helpers.py", True),
        ("test_cli.py", True),
        ("pkg/module_test.py", True),
        ("tests/conftest.py", True),
        ("conftest.py", True),
        ("src/app.py", False),
        ("src/latest_news.py", False),        # "test" inside a word
        ("contest/entry.py", False),
    ])
    def test_paths(self, path, expected):
        assert is_test_file(_ctx(path=path), "assert True\n") is expected


class TestOctalWithoutOtherWrite:
    @pytest.mark.parametrize("line_text,expected", [
        ("hook_path.chmod(0o755)", True),      # o+rx, no o+w → FP
        ("os.chmod(p, 0o644)", True),
        ("os.chmod(p, 0o777)", False),         # o+w → real
        ("os.chmod(p, 0o646)", False),         # o=6 has write bit
        ("p.chmod(0o4755)", True),             # setuid + 755, still no o+w
        ("some_line_without_octal()", False),  # cannot confirm FP → don't suppress
    ])
    def test_lines(self, line_text, expected):
        content = f"import os\n{line_text}\n"
        assert octal_without_other_write(_ctx(line=2), content) is expected


class TestIsCliEntryPoint:
    def test_argparse_file_args_line_suppresses(self):
        content = (
            "import argparse\n"
            "def main(args):\n"
            "    output_path = Path(args.output)\n"
        )
        assert is_cli_entry_point(_ctx(line=3), content) is True

    def test_no_argparse_import_is_real(self):
        content = "from flask import request\npath = Path(request.args['p'])\n"
        assert is_cli_entry_point(_ctx(line=2), content) is False

    def test_argparse_but_line_not_args_is_real(self):
        content = "import argparse\npath = Path(user_supplied)\n"
        assert is_cli_entry_point(_ctx(line=2), content) is False


class TestMatchInStringLiteral:
    def test_todo_in_string_suppresses(self):
        content = 'assert "TODO" not in body, "Contains TODO placeholder"\n'  # crucible-ignore: no-todo-without-issue -- fixture text
        col = content.index("TODO") + 1
        assert match_in_string_literal(_ctx(line=1, column=col), content) is True

    def test_todo_in_comment_is_real(self):
        content = "x = 1  # TODO fix this\n"  # crucible-ignore: no-todo-without-issue -- fixture text
        col = content.index("TODO") + 1
        assert match_in_string_literal(_ctx(line=1, column=col), content) is False

    def test_missing_line_fails_open(self):
        assert match_in_string_literal(_ctx(line=99, column=1), "x = 1\n") is False


class TestSubprocessImportUsed:
    def test_used_import_suppresses(self):
        content = "import subprocess\nsubprocess.run(['ls'], check=True)\n"
        assert subprocess_import_used(_ctx(line=1), content) is True

    def test_unused_import_is_real(self):
        content = "import subprocess\nprint('never calls it')\n"
        assert subprocess_import_used(_ctx(line=1), content) is False


def test_registry_names_are_exact():
    assert set(PREDICATES) == {
        "is_test_file",
        "octal_without_other_write",
        "is_cli_entry_point",
        "match_in_string_literal",
        "subprocess_import_used",
    }
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_verify_predicates.py -q` → FAIL (`ModuleNotFoundError: crucible.verify`).
- [ ] **Step 3: Implement** — create empty `src/crucible/verify/__init__.py` and `src/crucible/verify/predicates.py`:

```python
"""Context predicates for the Phase 6 verifier.

Each predicate answers: "is this finding a confirmed false positive?"
(True = suppress). They are written in the suppress direction so bindings
never need invert flags. All are pure functions over the finding's
location context and the file content; on any doubt they return False —
the verifier must never eat a true positive.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass(frozen=True)
class FindingContext:
    """Normalized location view of a finding, tool- and assertion-agnostic."""

    path: str
    line: int | None
    column: int | None
    match_text: str | None


def _line_at(content: str, line: int | None) -> str | None:
    if line is None or line < 1:
        return None
    lines = content.splitlines()
    if line > len(lines):
        return None
    return lines[line - 1]


def is_test_file(ctx: FindingContext, content: str) -> bool:
    """Corpus group 3 (bandit/B101): pytest uses assert as its mechanism."""
    path = PurePosixPath(ctx.path.replace("\\", "/"))
    if any(part in ("tests", "test") for part in path.parts[:-1]):
        return True
    name = path.name
    return (
        (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


_OCTAL_RE = re.compile(r"0o([0-7]{3,4})")


def octal_without_other_write(ctx: FindingContext, content: str) -> bool:
    """Corpus group 2 (world-writable-permissions): parse the octal at the
    match; suppress only when the other-write bit (0o2) is absent."""
    line = _line_at(content, ctx.line)
    if line is None:
        return False
    octals = _OCTAL_RE.findall(line)
    if not octals:
        return False
    return all(int(digits[-1], 8) & 0o2 == 0 for digits in octals)


_ARGPARSE_IMPORT_RE = re.compile(
    r"^\s*(import argparse\b|from argparse import\b)", re.MULTILINE
)


def is_cli_entry_point(ctx: FindingContext, content: str) -> bool:
    """Corpus group 1 (user-input-in-path): argparse output is
    operator-controlled — the CLI trust model, not the HTTP one."""
    if not _ARGPARSE_IMPORT_RE.search(content):
        return False
    line = _line_at(content, ctx.line)
    if line is None:
        return False
    return re.search(r"\bargs\.\w+", line) is not None


def match_in_string_literal(ctx: FindingContext, content: str) -> bool:
    """Corpus group 5 (no-todo-without-issue): a match inside a string
    literal is prose about the token, not a live comment marker."""
    line = _line_at(content, ctx.line)
    if line is None or ctx.column is None or ctx.column < 1:
        return False
    prefix = line[: ctx.column - 1]
    in_single = in_double = False
    escaped = False
    comment_start = False
    for ch in prefix:
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
        elif ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            comment_start = True
            break
    if comment_start:
        return False  # the match sits in a comment → real finding
    return in_single or in_double


_SUBPROCESS_USE_RE = re.compile(
    r"\bsubprocess\.(run|Popen|call|check_call|check_output)\s*\("
)


def subprocess_import_used(ctx: FindingContext, content: str) -> bool:
    """Corpus group 4 (bandit/B404): an exercised import is the feature;
    the usage-level bandit rules still police the calls themselves."""
    return _SUBPROCESS_USE_RE.search(content) is not None


PREDICATES: dict[str, Callable[[FindingContext, str], bool]] = {
    "is_test_file": is_test_file,
    "octal_without_other_write": octal_without_other_write,
    "is_cli_entry_point": is_cli_entry_point,
    "match_in_string_literal": match_in_string_literal,
    "subprocess_import_used": subprocess_import_used,
}
```

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_verify_predicates.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add src/crucible/verify tests/test_verify_predicates.py && git commit -m "feat: verifier context predicates (Phase 6)"`

---

### Task 3: Bindings cascade + bundled verifiers.yaml

**Files:**
- Create: `src/crucible/verify/bindings.py`
- Create: `src/crucible/verify/bundled/verifiers.yaml`
- Test: `tests/test_verify_bindings.py`

**Interfaces:**
- Consumes: `PREDICATES` (Task 2) for validation.
- Produces:
  - `VerifierBinding` frozen dataclass: `rule: str`, `predicate: str`, `reason: str`.
  - `load_bindings() -> tuple[dict[str, VerifierBinding], list[str]]` — bindings keyed by rule, plus error strings. Cascade first-found-wins per rule: `VERIFIERS_PROJECT` (`.crucible/verifiers.yaml`) → `VERIFIERS_USER` (`~/.claude/crucible/verifiers.yaml`) → `VERIFIERS_BUNDLED` (packaged). `disable:` lists from any file remove the rule entirely. Unknown predicate → error + binding skipped. Malformed YAML → error + file skipped.
  - Module-level path constants `VERIFIERS_PROJECT`, `VERIFIERS_USER`, `VERIFIERS_BUNDLED` (patchable in tests, same convention as `crucible.enforcement.assertions`).

- [ ] **Step 1: Write the failing tests** — create `tests/test_verify_bindings.py`:

```python
"""Cascade resolution tests for verifier bindings."""

from pathlib import Path
from unittest.mock import patch

from crucible.verify.bindings import load_bindings


def _patch_paths(tmp_path: Path, project=None, user=None, bundled=None):
    return (
        patch("crucible.verify.bindings.VERIFIERS_PROJECT",
              project or tmp_path / "none-project.yaml"),
        patch("crucible.verify.bindings.VERIFIERS_USER",
              user or tmp_path / "none-user.yaml"),
        patch("crucible.verify.bindings.VERIFIERS_BUNDLED",
              bundled or tmp_path / "none-bundled.yaml"),
    )


def test_bundled_ships_all_five_corpus_bindings():
    bindings, errors = load_bindings()
    assert errors == []
    assert bindings["bandit/B101"].predicate == "is_test_file"
    assert bindings["bandit/B404"].predicate == "subprocess_import_used"
    assert bindings["world-writable-permissions"].predicate == "octal_without_other_write"
    assert bindings["user-input-in-path"].predicate == "is_cli_entry_point"
    assert bindings["no-todo-without-issue"].predicate == "match_in_string_literal"
    assert all(b.reason for b in bindings.values())


def test_project_overrides_bundled(tmp_path: Path):
    proj = tmp_path / "verifiers.yaml"
    proj.write_text(
        "verifiers:\n"
        "  - rule: bandit/B101\n"
        "    predicate: subprocess_import_used\n"
        "    reason: project override\n"
    )
    bundled = tmp_path / "bundled.yaml"
    bundled.write_text(
        "verifiers:\n"
        "  - rule: bandit/B101\n"
        "    predicate: is_test_file\n"
        "    reason: bundled\n"
    )
    p1, p2, p3 = _patch_paths(tmp_path, project=proj, bundled=bundled)
    with p1, p2, p3:
        bindings, errors = load_bindings()
    assert errors == []
    assert bindings["bandit/B101"].predicate == "subprocess_import_used"


def test_disable_removes_rule(tmp_path: Path):
    proj = tmp_path / "verifiers.yaml"
    proj.write_text("disable:\n  - bandit/B101\n")
    bundled = tmp_path / "bundled.yaml"
    bundled.write_text(
        "verifiers:\n"
        "  - rule: bandit/B101\n"
        "    predicate: is_test_file\n"
        "    reason: bundled\n"
    )
    p1, p2, p3 = _patch_paths(tmp_path, project=proj, bundled=bundled)
    with p1, p2, p3:
        bindings, errors = load_bindings()
    assert "bandit/B101" not in bindings
    assert errors == []


def test_unknown_predicate_errors_and_skips(tmp_path: Path):
    proj = tmp_path / "verifiers.yaml"
    proj.write_text(
        "verifiers:\n"
        "  - rule: my-rule\n"
        "    predicate: no_such_predicate\n"
        "    reason: oops\n"
    )
    p1, p2, p3 = _patch_paths(tmp_path, project=proj)
    with p1, p2, p3:
        bindings, errors = load_bindings()
    assert "my-rule" not in bindings
    assert any("no_such_predicate" in e for e in errors)


def test_malformed_yaml_errors_and_skips_file(tmp_path: Path):
    proj = tmp_path / "verifiers.yaml"
    proj.write_text("{ not yaml [")
    p1, p2, p3 = _patch_paths(tmp_path, project=proj)
    with p1, p2, p3:
        bindings, errors = load_bindings()
    assert bindings == {}
    assert len(errors) == 1
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_verify_bindings.py -q` → FAIL (no `bindings` module).
- [ ] **Step 3: Implement** — create `src/crucible/verify/bundled/verifiers.yaml`:

```yaml
# Bundled verifier bindings — rule -> predicate. Each entry names a
# known-false-positive shape from docs/v2/phase6_verifier_corpus.md.
# Projects extend or disable via .crucible/verifiers.yaml (same shape;
# `disable:` lists rule keys to turn off entirely).
verifiers:
  - rule: bandit/B101
    predicate: is_test_file
    reason: "assert is pytest's mechanism; test runs never use -O"
  - rule: bandit/B404
    predicate: subprocess_import_used
    reason: "an exercised subprocess import is the feature; usage-level rules still police the calls"
  - rule: world-writable-permissions
    predicate: octal_without_other_write
    reason: "the octal grants no other-write bit (0o755-style exec perms)"
  - rule: user-input-in-path
    predicate: is_cli_entry_point
    reason: "argparse input is operator-controlled; the CLI operator is the trust boundary"
  - rule: no-todo-without-issue
    predicate: match_in_string_literal
    reason: "the token sits inside a string literal, not a live comment"
```

Then create `src/crucible/verify/bindings.py`:

```python
"""Verifier bindings: rule -> predicate, resolved through the cascade.

Same priority convention as every other crucible surface:
project (.crucible/) -> user (~/.claude/crucible/) -> bundled.
First binding found for a rule wins; a `disable:` entry in any file
removes the rule outright.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from crucible.verify.predicates import PREDICATES

VERIFIERS_PROJECT = Path(".crucible") / "verifiers.yaml"
VERIFIERS_USER = Path.home() / ".claude" / "crucible" / "verifiers.yaml"
VERIFIERS_BUNDLED = Path(__file__).resolve().parent / "bundled" / "verifiers.yaml"


@dataclass(frozen=True)
class VerifierBinding:
    rule: str
    predicate: str
    reason: str


def _load_file(path: Path) -> tuple[list[dict], list[str], list[str]]:
    """(entries, disables, errors) from one verifiers.yaml; empty on missing."""
    if not path.exists():
        return [], [], []
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except (yaml.YAMLError, OSError) as e:
        return [], [], [f"verifiers: failed to load {path}: {e}"]
    if not isinstance(data, dict):
        return [], [], [f"verifiers: {path} is not a mapping"]
    entries = [e for e in (data.get("verifiers") or []) if isinstance(e, dict)]
    disables = [str(d) for d in (data.get("disable") or [])]
    return entries, disables, []


def load_bindings() -> tuple[dict[str, VerifierBinding], list[str]]:
    """Resolve bindings through the cascade. Returns ({rule: binding}, errors)."""
    bindings: dict[str, VerifierBinding] = {}
    disables: set[str] = set()
    errors: list[str] = []

    for path in (VERIFIERS_PROJECT, VERIFIERS_USER, VERIFIERS_BUNDLED):
        entries, file_disables, file_errors = _load_file(path)
        errors.extend(file_errors)
        disables.update(file_disables)
        for entry in entries:
            rule = str(entry.get("rule", "")).strip()
            predicate = str(entry.get("predicate", "")).strip()
            reason = str(entry.get("reason", "")).strip()
            if not rule or not predicate:
                errors.append(f"verifiers: entry missing rule/predicate in {path}")
                continue
            if predicate not in PREDICATES:
                errors.append(
                    f"verifiers: unknown predicate '{predicate}' for rule "
                    f"'{rule}' in {path} — binding skipped"
                )
                continue
            if rule not in bindings:  # first found (highest priority) wins
                bindings[rule] = VerifierBinding(rule=rule, predicate=predicate, reason=reason)

    for rule in disables:
        bindings.pop(rule, None)
    return bindings, errors
```

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_verify_bindings.py -q` → PASS.
- [ ] **Step 5: Verify packaging picks up the yaml** — `python -m build --wheel >/dev/null 2>&1 && unzip -l dist/*.whl | grep verifiers.yaml` → must list `crucible/verify/bundled/verifiers.yaml`. If absent, add the pattern to `[tool.setuptools.package-data]` in `pyproject.toml` (follow the existing entries that ship `policies/*.yaml`), rebuild, re-check. Then `rm -rf dist build`.
- [ ] **Step 6: Commit** — `git add src/crucible/verify/bindings.py src/crucible/verify/bundled/verifiers.yaml tests/test_verify_bindings.py pyproject.toml && git commit -m "feat: verifier bindings cascade + bundled corpus bindings"` (drop `pyproject.toml` from the add if Step 5 needed no change).

---

### Task 4: run_verification core

**Files:**
- Create: `src/crucible/verify/core.py`
- Modify: `src/crucible/verify/__init__.py`
- Test: `tests/test_verify_core.py`

**Interfaces:**
- Consumes: `PREDICATES`, `FindingContext` (Task 2); `load_bindings` (Task 3); `ToolFinding.suppressed` (Task 1); `EnforcementFinding` (existing — fields `assertion_id`, `location`, `suppressed`, `suppression_reason`).
- Produces (re-exported from `crucible.verify`):
  - `run_verification(tool_findings, enforcement_findings, repo_root=None, file_contents=None) -> tuple[list[ToolFinding], list[EnforcementFinding], list[str]]`.
  - Rule keys: `f"{finding.tool}/{finding.rule}"` for tool findings, `finding.assertion_id` for enforcement findings.
  - `file_contents: dict[str, str] | None` — in-memory override keyed by the finding's path, used by the Claude Code hooks (proposed content not yet on disk) and by tests.

- [ ] **Step 1: Write the failing tests** — create `tests/test_verify_core.py`:

```python
"""Unit tests for run_verification: marking, passthrough, fail-open."""

from pathlib import Path
from unittest.mock import patch

from crucible.enforcement.models import EnforcementFinding, Priority
from crucible.models import Severity, ToolFinding
from crucible.verify import run_verification


def _b101(path="tests/test_x.py", line=3):
    return ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                       message="assert used", location=f"{path}:{line}")


def _todo_finding(path, line, col):
    return EnforcementFinding(
        assertion_id="no-todo-without-issue",
        message="TODO comments should reference an issue number",  # crucible-ignore: no-todo-without-issue -- fixture text
        severity="info", priority=Priority.LOW,
        location=f"{path}:{line}:{col}",
    )


class TestMarking:
    def test_bound_tool_finding_suppressed(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("import x\n\nassert x\n")
        tools, enf, errors = run_verification([_b101()], [], repo_root=str(tmp_path))
        assert tools[0].suppressed is True
        assert tools[0].suppression_reason.startswith("verifier:is_test_file")
        assert errors == []

    def test_enforcement_finding_suppressed_via_file_contents(self) -> None:
        content = 'assert "TODO" not in body\n'  # crucible-ignore: no-todo-without-issue -- fixture text
        col = content.index("TODO") + 1
        f = _todo_finding("tests/test_skills.py", 1, col)
        tools, enf, errors = run_verification(
            [], [f], file_contents={"tests/test_skills.py": content})
        assert enf[0].suppressed is True

    def test_unbound_rule_passes_through(self, tmp_path: Path) -> None:
        f = ToolFinding(tool="semgrep", rule="anything", severity=Severity.HIGH,
                        message="x", location="src/app.py:1")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x = 1\n")
        tools, _, errors = run_verification([f], [], repo_root=str(tmp_path))
        assert tools[0].suppressed is False
        assert errors == []

    def test_predicate_false_passes_through(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("assert x\n")
        f = _b101(path="src/app.py", line=1)
        tools, _, _ = run_verification([f], [], repo_root=str(tmp_path))
        assert tools[0].suppressed is False

    def test_already_suppressed_untouched(self, tmp_path: Path) -> None:
        f = EnforcementFinding(
            assertion_id="no-todo-without-issue", message="m", severity="info",
            priority=Priority.LOW, location="a.py:1:1",
            suppressed=True, suppression_reason="inline",
        )
        _, enf, _ = run_verification([], [f], file_contents={"a.py": "x\n"})
        assert enf[0].suppression_reason == "inline"


class TestFailOpen:
    def test_unreadable_file_passes_through(self, tmp_path: Path) -> None:
        tools, _, errors = run_verification([_b101()], [], repo_root=str(tmp_path))
        assert tools[0].suppressed is False  # file doesn't exist → no suppression

    def test_predicate_exception_passes_through(self, tmp_path: Path) -> None:
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_x.py").write_text("assert x\n")

        def boom(ctx, content):
            raise RuntimeError("predicate bug")

        with patch.dict("crucible.verify.predicates.PREDICATES",
                        {"is_test_file": boom}):
            tools, _, _ = run_verification([_b101()], [], repo_root=str(tmp_path))
        assert tools[0].suppressed is False

    def test_binding_errors_surface(self, tmp_path: Path) -> None:
        proj = tmp_path / "verifiers.yaml"
        proj.write_text("{ not yaml [")
        with patch("crucible.verify.bindings.VERIFIERS_PROJECT", proj):
            _, _, errors = run_verification([], [])
        assert len(errors) == 1
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_verify_core.py -q` → FAIL (no `run_verification`).
- [ ] **Step 3: Implement** — create `src/crucible/verify/core.py`:

```python
"""run_verification: apply bound predicates to findings, marking false
positives suppressed. Marks, never drops; unbound rules pass through;
every internal failure fails open toward showing the finding."""

from __future__ import annotations

import dataclasses
import os

from crucible.enforcement.models import EnforcementFinding
from crucible.models import ToolFinding
from crucible.verify.bindings import load_bindings
from crucible.verify.predicates import PREDICATES, FindingContext


def _split_location(location: str) -> tuple[str, int | None, int | None]:
    """'path:line:col' | 'path:line' | 'path' -> (path, line, col)."""
    parts = location.rsplit(":", 2)
    if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
        return parts[0], int(parts[1]), int(parts[2])
    head = location.rsplit(":", 1)
    if len(head) == 2 and head[1].isdigit():
        return head[0], int(head[1]), None
    return location, None, None


def _read(path: str, repo_root: str | None,
          file_contents: dict[str, str] | None,
          cache: dict[str, str | None]) -> str | None:
    if file_contents is not None and path in file_contents:
        return file_contents[path]
    if path in cache:
        return cache[path]
    full = os.path.join(repo_root, path) if repo_root else path
    try:
        with open(full, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        content = None
    cache[path] = content
    return content


def run_verification(
    tool_findings: list[ToolFinding],
    enforcement_findings: list[EnforcementFinding],
    repo_root: str | None = None,
    file_contents: dict[str, str] | None = None,
) -> tuple[list[ToolFinding], list[EnforcementFinding], list[str]]:
    bindings, errors = load_bindings()
    if not bindings:
        return tool_findings, enforcement_findings, errors

    cache: dict[str, str | None] = {}

    def verify(finding, rule_key: str, match_text: str | None):
        if finding.suppressed or rule_key not in bindings:
            return finding
        binding = bindings[rule_key]
        path, line, col = _split_location(finding.location)
        content = _read(path, repo_root, file_contents, cache)
        if content is None:
            return finding  # unreadable → fail open
        ctx = FindingContext(path=path, line=line, column=col, match_text=match_text)
        try:
            is_fp = PREDICATES[binding.predicate](ctx, content)
        except Exception:  # crucible-ignore: no-catch-exception -- fail-open boundary: a predicate bug must never hide a finding
            return finding
        if not is_fp:
            return finding
        return dataclasses.replace(
            finding,
            suppressed=True,
            suppression_reason=f"verifier:{binding.predicate} — {binding.reason}",
        )

    verified_tools = [
        verify(f, f"{f.tool}/{f.rule}", None) for f in tool_findings
    ]
    verified_enforcement = [
        verify(f, f.assertion_id, getattr(f, "match_text", None))
        for f in enforcement_findings
    ]
    return verified_tools, verified_enforcement, errors
```

Replace `src/crucible/verify/__init__.py` content:

```python
"""Phase 6 verifier: deterministic false-positive suppression."""

from crucible.verify.bindings import VerifierBinding, load_bindings
from crucible.verify.core import run_verification
from crucible.verify.predicates import PREDICATES, FindingContext

__all__ = [
    "PREDICATES",
    "FindingContext",
    "VerifierBinding",
    "load_bindings",
    "run_verification",
]
```

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_verify_core.py tests/test_verify_predicates.py tests/test_verify_bindings.py -q` → PASS. Also `ruff check src/`.
- [ ] **Step 5: Commit** — `git add src/crucible/verify tests/test_verify_core.py && git commit -m "feat: run_verification core (Phase 6)"`

---

### Task 5: Enforced corpus eval

**Files:**
- Test: `tests/test_verifier_corpus.py` (create)

**Interfaces:**
- Consumes: `run_verification` (Task 4). No production code in this task — it is the acceptance gate from `docs/v2/phase6_verifier_corpus.md`: **125/125 suppressed**, control group 0 suppressed.

- [ ] **Step 1: Write the test** — create `tests/test_verifier_corpus.py`:

```python
"""The Phase 6 acceptance gate: every corpus false positive suppressed,
every control-group true positive passed through.

Corpus: docs/v2/phase6_verifier_corpus.md (125 findings across 5 groups).
Findings are reconstructed synthetically with matching file content so the
gate is hermetic — no semgrep/bandit/API needed.
"""

from pathlib import Path

from crucible.enforcement.models import EnforcementFinding, Priority
from crucible.models import Severity, ToolFinding
from crucible.verify import run_verification


def _tool(tool, rule, location, severity=Severity.LOW):
    return ToolFinding(tool=tool, rule=rule, severity=severity,
                       message=f"{rule} fired", location=location)


def _enf(assertion_id, location, severity="warning"):
    return EnforcementFinding(
        assertion_id=assertion_id, message=f"{assertion_id} fired",
        severity=severity, priority=Priority.MEDIUM, location=location,
    )


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def _build_corpus(root: Path):
    """Returns (tool_findings, enforcement_findings) — 125 total."""
    tool_findings, enforcement_findings = [], []

    # Group 1 — user-input-in-path on argparse CLI (6)
    cli_lines = ["import argparse", "def main(args):"]
    for i in range(6):
        cli_lines.append(f"    p{i} = Path(args.field{i})")
    _write(root, "src/cli.py", "\n".join(cli_lines) + "\n")
    for i in range(6):
        enforcement_findings.append(_enf("user-input-in-path", f"src/cli.py:{3 + i}:5"))

    # Group 2 — world-writable-permissions on 0o755 (1)
    _write(root, "src/hooks.py", "import os\nhook_path.chmod(0o755)\n")
    enforcement_findings.append(_enf("world-writable-permissions", "src/hooks.py:2:1"))

    # Group 3 — bandit/B101 assert-in-tests (114)
    assert_lines = "\n".join(f"    assert value == {i}" for i in range(114))
    _write(root, "tests/test_sample.py", f"def test_all():\n{assert_lines}\n")
    for i in range(114):
        tool_findings.append(_tool("bandit", "B101", f"tests/test_sample.py:{2 + i}"))

    # Group 4 — bandit/B404 exercised subprocess import (1)
    _write(root, "src/delegation.py",
           "import subprocess\n\nsubprocess.run(['ls'], check=True)\n")
    tool_findings.append(_tool("bandit", "B404", "src/delegation.py:1"))

    # Group 5 — no-todo-without-issue inside string literals (3)
    todo_line = 'assert "TODO" not in text, "Contains TODO placeholder"'  # crucible-ignore: no-todo-without-issue -- fixture text
    _write(root, "tests/test_skills.py",
           "def test_no_placeholders():\n"
           f"    {todo_line}\n"
           f"    {todo_line}\n"
           f"    {todo_line}\n")
    for line in (2, 3, 4):
        col = 5 + todo_line.index("TODO") + 1
        enforcement_findings.append(_enf("no-todo-without-issue",
                                         f"tests/test_skills.py:{line}:{col}", "info"))

    assert len(tool_findings) + len(enforcement_findings) == 125
    return tool_findings, enforcement_findings


def test_corpus_fully_suppressed(tmp_path: Path) -> None:
    tools, enforcement = _build_corpus(tmp_path)
    v_tools, v_enf, errors = run_verification(tools, enforcement,
                                              repo_root=str(tmp_path))
    assert errors == []
    suppressed = sum(f.suppressed for f in v_tools) + sum(f.suppressed for f in v_enf)
    assert suppressed == 125, (
        f"corpus gate: {suppressed}/125 suppressed — unsuppressed: "
        + ", ".join(f"{f.location}" for f in [*v_tools, *v_enf] if not f.suppressed)[:2000]
    )


def test_control_group_never_suppressed(tmp_path: Path) -> None:
    """True positives that superficially resemble the corpus must survive."""
    _write(tmp_path, "src/handler.py",
           "from flask import request\npath = Path(request.args['p'])\n")
    _write(tmp_path, "src/perm.py", "import os\nos.chmod(p, 0o777)\n")
    _write(tmp_path, "src/prod.py", "assert config is not None\n")
    _write(tmp_path, "src/unused.py", "import subprocess\nprint('never used')\n")
    _write(tmp_path, "src/todo.py", "x = 1  # TODO fix this\n")  # crucible-ignore: no-todo-without-issue -- fixture text

    todo_col = 8 + 1  # column of the token after "x = 1  # "
    controls_tools = [
        _tool("bandit", "B101", "src/prod.py:1"),
        _tool("bandit", "B404", "src/unused.py:1"),
    ]
    controls_enf = [
        _enf("user-input-in-path", "src/handler.py:2:8"),
        _enf("world-writable-permissions", "src/perm.py:2:1"),
        _enf("no-todo-without-issue", f"src/todo.py:1:{todo_col}", "info"),
    ]
    v_tools, v_enf, _ = run_verification(controls_tools, controls_enf,
                                         repo_root=str(tmp_path))
    survivors = [f for f in [*v_tools, *v_enf] if f.suppressed]
    assert survivors == [], f"control-group true positives suppressed: {survivors}"
```

- [ ] **Step 2: Run it** — `python -m pytest tests/test_verifier_corpus.py -q` → both tests PASS. If the gate fails, fix the *predicate or binding* (Tasks 2–3), never weaken the test.
- [ ] **Step 3: Run the full verify suite** — `python -m pytest tests/test_verify_predicates.py tests/test_verify_bindings.py tests/test_verify_core.py tests/test_verifier_corpus.py -q` → PASS.
- [ ] **Step 4: Commit** — `git add tests/test_verifier_corpus.py && git commit -m "test: enforced 125/125 verifier corpus gate"`

---

### Task 6: Suppression-aware severity counts

**Files:**
- Modify: `src/crucible/review/core.py:295-302` (`compute_severity_counts`)
- Test: `tests/test_full_review.py` (append)

**Interfaces:**
- Produces: `compute_severity_counts` skips findings with `suppressed=True`. Signature unchanged: `(findings: list[ToolFinding]) -> dict[str, int]`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_full_review.py`:

```python
class TestSeverityCountsSkipSuppressed:
    def test_suppressed_not_counted(self) -> None:
        import dataclasses

        from crucible.models import Severity, ToolFinding
        from crucible.review.core import compute_severity_counts

        active = ToolFinding(tool="bandit", rule="B102", severity=Severity.HIGH,
                             message="m", location="a.py:1")
        muted = dataclasses.replace(
            ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                        message="m", location="tests/test_a.py:1"),
            suppressed=True, suppression_reason="verifier:is_test_file — t")
        counts = compute_severity_counts([active, muted])
        assert counts.get("high") == 1
        assert counts.get("low", 0) == 0
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_full_review.py -q` → FAIL (low counted).
- [ ] **Step 3: Implement** — in `compute_severity_counts` (review/core.py), add the skip at the top of the loop over findings:

```python
    for f in findings:
        if f.suppressed:
            continue
```

(keep the rest of the function unchanged).

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_full_review.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add src/crucible/review/core.py tests/test_full_review.py && git commit -m "feat: severity counts skip suppressed findings"`

---### Task 7: Parallel tool delegation

**Files:**
- Modify: `src/crucible/review/core.py:107-159` (`run_static_analysis`)
- Test: `tests/test_full_review.py` (append)

**Interfaces:**
- Produces: same signature and same fixed result order (semgrep, ruff, slither, bandit); delegates run concurrently via `ThreadPoolExecutor`.

- [ ] **Step 1: Write the failing test** — append to `tests/test_full_review.py`:

```python
class TestParallelDelegation:
    def test_wall_clock_beats_sequential(self, tmp_path) -> None:
        import time
        from unittest.mock import patch

        from crucible.errors import ok
        from crucible.models import Domain
        from crucible.review.core import run_static_analysis

        def slow(name):
            def delegate(*args, **kwargs):
                time.sleep(0.3)
                return ok([])
            return delegate

        with (
            patch("crucible.review.core.delegate_semgrep", slow("semgrep")),
            patch("crucible.review.core.delegate_ruff", slow("ruff")),
            patch("crucible.review.core.delegate_slither", slow("slither")),
            patch("crucible.review.core.delegate_bandit", slow("bandit")),
        ):
            start = time.monotonic()
            findings, errors = run_static_analysis(
                str(tmp_path), Domain.BACKEND, ["python"],
                tools=["semgrep", "ruff", "slither", "bandit"])
            elapsed = time.monotonic() - start
        assert errors == []
        assert elapsed < 0.9, f"4×0.3s delegates took {elapsed:.2f}s — not parallel"

    def test_error_aggregation_and_order(self, tmp_path) -> None:
        from unittest.mock import patch

        from crucible.errors import err, ok
        from crucible.models import Domain, Severity, ToolFinding
        from crucible.review.core import run_static_analysis

        f_ruff = ToolFinding(tool="ruff", rule="E1", severity=Severity.LOW,
                             message="m", location="a.py:1")
        with (
            patch("crucible.review.core.delegate_semgrep",
                  lambda *a, **k: err("semgrep exploded")),
            patch("crucible.review.core.delegate_ruff", lambda *a, **k: ok([f_ruff])),
        ):
            findings, errors = run_static_analysis(
                str(tmp_path), Domain.BACKEND, ["python"], tools=["semgrep", "ruff"])
        assert findings == [f_ruff]
        assert errors == ["semgrep: semgrep exploded"]
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_full_review.py::TestParallelDelegation -q` → the wall-clock test FAILS (~1.2s sequential).
- [ ] **Step 3: Implement** — replace the body of `run_static_analysis` after the `tools` default resolution:

```python
    from concurrent.futures import ThreadPoolExecutor

    all_findings: list[ToolFinding] = []
    tool_errors: list[str] = []

    # (name, thunk) in canonical order; delegates are subprocess-wait-bound,
    # so threads give real wall-clock overlap.
    jobs: list[tuple[str, Callable[[], Result]]] = []
    if "semgrep" in tools:
        config = get_semgrep_config(domain)
        jobs.append(("semgrep", lambda: delegate_semgrep(path, config)))
    if "ruff" in tools:
        jobs.append(("ruff", lambda: delegate_ruff(path)))
    if "slither" in tools:
        jobs.append(("slither", lambda: delegate_slither(path)))
    if "bandit" in tools:
        jobs.append(("bandit", lambda: delegate_bandit(path)))

    if not jobs:
        return all_findings, tool_errors

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = [(name, pool.submit(thunk)) for name, thunk in jobs]
        for name, future in futures:  # fixed submission order → deterministic output
            result = future.result()
            if result.is_ok:
                all_findings.extend(result.value)
            else:
                tool_errors.append(f"{name}: {result.error}")

    return all_findings, tool_errors
```

Add the imports the block needs at the top of the file: `from collections.abc import Callable` and `from crucible.errors import Result` (check what is already imported first).

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_full_review.py -q` → PASS. `ruff check src/`.
- [ ] **Step 5: Commit** — `git add src/crucible/review/core.py tests/test_full_review.py && git commit -m "feat: parallel static-analysis delegation"`

---

### Task 8: Wire verifier into CLI review (both modes) + display

**Files:**
- Modify: `src/crucible/cli.py` — path-review (`run_static_analysis` call at ~:773, `run_enforcement` at ~:791, counts at ~:802, display ~:850-880) and git-review (`run_enforcement` at ~:1101, enforcement split at ~:1322-1335; locate the git-mode `run_static_analysis` call with `grep -n "run_static_analysis" src/crucible/cli.py`)
- Test: `tests/test_cli.py` (append)

**Interfaces:**
- Consumes: `run_verification` (Task 4).
- Produces: both CLI review paths call `run_verification(findings, enforcement_findings, repo_root=...)` immediately after both finding lists exist and before counts/threshold/display. New flag `--no-verify` on the `review` command (`verify = not args.no_verify`; when False, skip the call). Display: suppressed findings excluded from the main lists and shown as a `Suppressed by verifier (N):` section listing `location rule — reason` when N > 0.

- [ ] **Step 1: Write the failing test** — append to `tests/test_cli.py`:

```python
class TestReviewVerification:
    def test_review_suppresses_corpus_shapes(self, tmp_path, monkeypatch, capsys) -> None:
        """A B101-style finding in a test file is suppressed end to end."""
        import dataclasses
        from unittest.mock import patch

        from crucible.models import Severity, ToolFinding

        monkeypatch.chdir(tmp_path)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("assert True\n")

        finding = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                              message="assert used", location="tests/test_a.py:1")
        with patch("crucible.review.core.delegate_bandit",
                   lambda *a, **k: __import__("crucible.errors", fromlist=["ok"]).ok([finding])):
            from crucible.cli import main
            code = main(["review", "tests/", "--no-git"])

        out = capsys.readouterr().out
        assert "Suppressed by verifier (1)" in out
        assert code == 0
```

Adapt the invocation to the actual CLI entry (`main(argv)` vs `cmd_review(args)`) — read the existing tests in `tests/test_cli.py` first and copy their invocation pattern exactly; the assertion lines stay as written.

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_cli.py -q` → FAIL (no suppressed section).
- [ ] **Step 3: Implement** — in both review paths of `cli.py`, after tool findings and enforcement findings both exist:

```python
    if not getattr(args, "no_verify", False):
        from crucible.verify import run_verification
        all_findings, enforcement_findings, verify_errors = run_verification(
            all_findings, enforcement_findings, repo_root=repo_root_or_none)
        errors.extend(verify_errors)
```

(`repo_root_or_none`: the git repo root in git mode; `None` in `--no-git` path mode where locations are already cwd-relative.) In each display section, split before printing:

```python
    verifier_suppressed = [f for f in all_findings if f.suppressed] + [
        f for f in enforcement_findings
        if f.suppressed and (f.suppression_reason or "").startswith("verifier:")
    ]
    active_findings = [f for f in all_findings if not f.suppressed]
```

Print `active_findings` where the code printed `all_findings`; keep the existing enforcement active/suppressed split; then after the finding lists:

```python
    if verifier_suppressed:
        print(f"\nSuppressed by verifier ({len(verifier_suppressed)}):")
        for f in verifier_suppressed:
            rule = f"{f.tool}/{f.rule}" if hasattr(f, "tool") else f.assertion_id
            print(f"  {f.location} {rule} — {f.suppression_reason}")
```

Register the flag next to the other `review` command arguments:

```python
    review_parser.add_argument(
        "--no-verify", action="store_true",
        help="Skip the false-positive verifier (show raw findings)")
```

Add the same flag to the path-review parser if it is a separate subparser (check with `grep -n "no-git\|add_argument" src/crucible/cli.py | grep -A2 review`).

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_cli.py -q` → PASS.
- [ ] **Step 5: Live dogfood** — `crucible review src/crucible/cli.py --no-git` → the corpus Group 1/2 findings (`user-input-in-path` ×6, `world-writable-permissions` ×1) must now appear under "Suppressed by verifier", not as warnings. This is the corpus doc's "How to use" measurement — record the observed suppression in the task summary.
- [ ] **Step 6: Commit** — `git add src/crucible/cli.py tests/test_cli.py && git commit -m "feat: wire verifier into CLI review with suppressed display"`

---

### Task 9: Wire verifier into MCP review

**Files:**
- Modify: `src/crucible/server.py` (after `run_static_analysis` ~:617/:629 and `run_enforcement` ~:651/:660, before `compute_severity_counts` ~:664; suppressed display exists at ~:428-491 for enforcement — extend to tool findings)
- Test: `tests/test_server.py` (append)

**Interfaces:**
- Consumes: `run_verification` (Task 4).
- Produces: the MCP `review` tool verifies both finding lists before counts; verifier-suppressed tool findings appear in the existing `*Suppressed:*` section alongside enforcement ones.

- [ ] **Step 1: Write the failing test** — append to `tests/test_server.py`, copying the file's existing pattern for invoking the review tool with mocked delegates (there are existing tests that patch `crucible.review.core.delegate_*` or `run_static_analysis`; mirror one):

```python
class TestReviewVerifierIntegration:
    def test_b101_in_tests_suppressed(self, tmp_path) -> None:
        from unittest.mock import patch

        from crucible.errors import ok
        from crucible.models import Severity, ToolFinding

        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").write_text("assert True\n")
        finding = ToolFinding(tool="bandit", rule="B101", severity=Severity.LOW,
                              message="assert used",
                              location=str(tmp_path / "tests" / "test_a.py") + ":1")

        with patch("crucible.review.core.delegate_bandit", lambda *a, **k: ok([finding])), \
             patch("crucible.review.core.delegate_ruff", lambda *a, **k: ok([])), \
             patch("crucible.review.core.delegate_semgrep", lambda *a, **k: ok([])):
            # invoke the review path the same way neighboring tests do
            result_text = _run_review_tool(path=str(tmp_path / "tests"))

        assert "Suppressed" in result_text
        assert "B101" not in result_text.split("Suppressed")[0]
```

Replace `_run_review_tool` with the invocation helper used by the neighboring tests in `tests/test_server.py` (read the file first; keep the two assertions).

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_server.py -q` → FAIL.
- [ ] **Step 3: Implement** — in `server.py` after both finding lists exist and before `compute_severity_counts`:

```python
        from crucible.verify import run_verification
        all_findings, enforcement_findings, verify_errors = run_verification(
            all_findings, enforcement_findings)
        errors.extend(verify_errors)
```

Then extend the suppressed rendering (~:428-491): where `active`/`suppressed` are computed for enforcement findings, also compute `active_tools = [f for f in all_findings if not f.suppressed]` / `suppressed_tools = [...]`, render `active_tools` in the main list, and include `suppressed_tools` in the `*Suppressed: N*` section with `{f.location} {f.tool}/{f.rule} — {f.suppression_reason}` lines.

- [ ] **Step 4: Run to verify it passes** — `python -m pytest tests/test_server.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add src/crucible/server.py tests/test_server.py && git commit -m "feat: wire verifier into MCP review tool"`

---

### Task 10: Wire verifier into pre-commit + Claude Code hooks

**Files:**
- Modify: `src/crucible/hooks/precommit.py` (`PrecommitConfig` at :112-132; `run_precommit` after the enforcement block at ~:509-522 and before the tool-finding threshold logic)
- Modify: `src/crucible/hooks/claudecode.py` (`_evaluate_content`)
- Test: `tests/test_precommit.py`, `tests/test_pretool_hook.py` (append)

**Interfaces:**
- Consumes: `run_verification` with `file_contents` (Task 4).
- Produces: `PrecommitConfig.verify: bool = True` (read from `precommit.yaml` key `verify`); `run_precommit` verifies both lists (deterministic tier only). `_evaluate_content` verifies its enforcement findings with `file_contents={file_path: content}` so the pretool hook (content not on disk) works; config key `verify: true` default in `claudecode.yaml` via `ClaudeCodeHookConfig.verify: bool = True`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_precommit.py` (inside/next to `TestEnforcementSuppression`, reusing its `_repo_with_staged` helper):

```python
class TestVerifierInPrecommit:
    def test_b101_style_fp_does_not_fail_gate(self, tmp_path) -> None:
        """A bound FP shape in staged changes is suppressed by the verifier."""
        # Reuse _repo_with_staged but stage a test file with an assert and
        # configure a project assertion that fires on it, bound in
        # .crucible/verifiers.yaml via the bundled bandit/B101... simpler:
        # use the bundled no-todo binding with an enforcement assertion.
        repo = TestEnforcementSuppression()._repo_with_staged(
            tmp_path,
            'msg = "TODO is discussed here"\n',  # crucible-ignore: no-todo-without-issue -- fixture text
        )
        assertions_dir = repo / ".crucible" / "assertions"
        (assertions_dir / "todo.yaml").write_text("""
assertions:
  - id: no-todo-without-issue
    type: pattern
    pattern: "TODO"
    message: "TODO needs issue"
    severity: error
""")
        result = TestEnforcementSuppression()._run(repo)
        assert result.passed, f"verifier should suppress string-literal TODO: {result}"
```

Append to `tests/test_pretool_hook.py`:

```python
class TestPretoolVerifier:
    def test_bound_fp_in_proposed_content_allowed(self, tmp_path) -> None:
        """String-literal TODO in proposed Write content is verifier-suppressed."""
        _assertions_dir(tmp_path)
        (tmp_path / ".crucible" / "assertions" / "todo.yaml").write_text("""
assertions:
  - id: no-todo-without-issue
    type: pattern
    pattern: "TODO"
    message: "TODO needs issue"
    severity: error
""")
        code = 'msg = "TODO handling is described here"\n'  # crucible-ignore: no-todo-without-issue -- fixture text
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "app.py", "content": code},
        })
        assert exit_code == 0
```

- [ ] **Step 2: Run to verify they fail** — `python -m pytest tests/test_precommit.py tests/test_pretool_hook.py -q` → both new tests FAIL (gate blocks).
- [ ] **Step 3: Implement precommit** — add to `PrecommitConfig`: `verify: bool = True`; in `load_precommit_config` read `verify: data.get("verify", True)` (follow the existing key pattern). In `run_precommit`, right after the Phase-5 suppression filter line (`enforcement_findings = [f for f in enforcement_findings if not f.suppressed]` — verification must run BEFORE that filter, so place this above it):

```python
        if config.verify:
            from crucible.verify import run_verification
            all_findings, enforcement_findings, _verify_errors = run_verification(
                all_findings, enforcement_findings, repo_root=repo_root)
        enforcement_findings = [f for f in enforcement_findings if not f.suppressed]
        all_findings = [f for f in all_findings if not f.suppressed]
```

(The pre-commit gate drops suppressed findings from output entirely — consistent with its existing handling of inline suppressions; the CLI/MCP surfaces are where suppressed findings are displayed.)

- [ ] **Step 4: Implement claudecode hooks** — add `verify: bool = True` to `ClaudeCodeHookConfig` + `load_claudecode_config` (`data.get("verify", True)`). In `_evaluate_content`, after `run_pattern_assertions` returns `findings` and before the severity filter:

```python
    if config.verify:
        from crucible.verify import run_verification
        _, findings, _ = run_verification(
            [], findings, file_contents={file_path: content})
```

(The existing severity filter already excludes `f.suppressed` findings, so no display change is needed.)

- [ ] **Step 5: Run to verify they pass** — `python -m pytest tests/test_precommit.py tests/test_pretool_hook.py tests/test_activation.py -q` → PASS. `ruff check src/`.
- [ ] **Step 6: Commit** — `git add src/crucible/hooks/precommit.py src/crucible/hooks/claudecode.py tests/test_precommit.py tests/test_pretool_hook.py && git commit -m "feat: verifier in pre-commit gate and coding hooks"`

---

### Task 11: LLM escalation tier (opt-in)

**Files:**
- Create: `src/crucible/verify/llm.py`
- Modify: `src/crucible/cli.py` (add `--verify-llm` to the review command; call after deterministic verification when set)
- Test: `tests/test_verify_llm.py` (create)

**Interfaces:**
- Consumes: `_get_anthropic_client` and `MODEL_IDS` from `crucible.enforcement.compliance`; `ToolFinding`/`EnforcementFinding` suppression fields.
- Produces: `run_llm_verification(tool_findings, enforcement_findings, repo_root=None, model="sonnet", token_budget=10000) -> tuple[list, list, list[str]]` — for findings still unsuppressed after the deterministic tier, asks the model to construct the strongest counterargument and suppresses only on a confident verdict. Uses **structured outputs** (`output_config={"format": {"type": "json_schema", ...}}`) so responses are schema-valid JSON — no brittle parsing (this addresses the parse failures noted in the spec follow-ups). API error / budget exhausted → findings pass through, error string appended.

- [ ] **Step 1: Write the failing tests** — create `tests/test_verify_llm.py`:

```python
"""LLM escalation tier — stubbed client, never live (conftest guards)."""

import json
from unittest.mock import MagicMock, patch

from crucible.models import Severity, ToolFinding
from crucible.verify.llm import run_llm_verification


def _finding():
    return ToolFinding(tool="semgrep", rule="custom-rule", severity=Severity.HIGH,
                       message="possible injection", location="src/app.py:10")


def _mock_client(suppress: bool, counterargument: str = "it is parameterized"):
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(type="text", text=json.dumps(
        {"suppress": suppress, "counterargument": counterargument}))]
    response.usage.input_tokens = 500
    response.usage.output_tokens = 50
    client.messages.create.return_value = response
    return client


class TestLLMVerification:
    def test_suppress_verdict_marks_finding(self, tmp_path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("query = db.execute(sql, params)\n" * 12)
        with patch("crucible.verify.llm._get_anthropic_client",
                   return_value=_mock_client(True)):
            tools, _, errors = run_llm_verification([_finding()], [],
                                                    repo_root=str(tmp_path))
        assert tools[0].suppressed is True
        assert "llm:" in tools[0].suppression_reason
        assert errors == []

    def test_keep_verdict_passes_through(self, tmp_path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x\n" * 12)
        with patch("crucible.verify.llm._get_anthropic_client",
                   return_value=_mock_client(False)):
            tools, _, _ = run_llm_verification([_finding()], [],
                                               repo_root=str(tmp_path))
        assert tools[0].suppressed is False

    def test_api_error_fails_open(self, tmp_path) -> None:
        with patch("crucible.verify.llm._get_anthropic_client",
                   side_effect=ValueError("no key")):
            tools, _, errors = run_llm_verification([_finding()], [],
                                                    repo_root=str(tmp_path))
        assert tools[0].suppressed is False
        assert len(errors) == 1

    def test_budget_exhaustion_stops_calls(self, tmp_path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.py").write_text("x\n")
        client = _mock_client(True)
        findings = [_finding() for _ in range(5)]
        with patch("crucible.verify.llm._get_anthropic_client", return_value=client):
            tools, _, errors = run_llm_verification(
                findings, [], repo_root=str(tmp_path), token_budget=600)
        # first call spends 550 tokens (>600 remaining budget after it) → later
        # findings skipped without calls
        assert client.messages.create.call_count == 2  # second call detects exhaustion
        assert any("budget" in e.lower() for e in errors)

    def test_already_suppressed_not_sent(self, tmp_path) -> None:
        import dataclasses
        f = dataclasses.replace(_finding(), suppressed=True,
                                suppression_reason="verifier:x — y")
        client = _mock_client(True)
        with patch("crucible.verify.llm._get_anthropic_client", return_value=client):
            run_llm_verification([f], [], repo_root=str(tmp_path))
        assert client.messages.create.call_count == 0
```

- [ ] **Step 2: Run to verify it fails** — `python -m pytest tests/test_verify_llm.py -q` → FAIL (no module).
- [ ] **Step 3: Implement** — create `src/crucible/verify/llm.py`:

```python
"""Opt-in LLM escalation tier: findings the deterministic verifier could
not decide get one adversarial pass — construct the strongest
counterargument; suppress only if it is materially stronger than the
finding's evidence. Structured outputs guarantee parseable verdicts."""

from __future__ import annotations

import dataclasses
import json
import os

from crucible.enforcement.compliance import MODEL_IDS, _get_anthropic_client
from crucible.enforcement.models import EnforcementFinding
from crucible.models import ToolFinding
from crucible.verify.core import _split_location

_VERDICT_SCHEMA = {
    "type": "json_schema",
    "schema": {
        "type": "object",
        "properties": {
            "suppress": {"type": "boolean"},
            "counterargument": {"type": "string"},
        },
        "required": ["suppress", "counterargument"],
        "additionalProperties": False,
    },
}

_SYSTEM = (
    "You are a code-review verifier. You receive one static-analysis "
    "finding plus file context. Construct the strongest counterargument "
    "that the finding is a false positive. Set suppress=true ONLY if that "
    "counterargument is materially stronger than the finding's evidence; "
    "when uncertain, set suppress=false — a shown false positive is "
    "cheaper than a hidden true positive."
)


def _context_snippet(content: str, line: int | None, radius: int = 10) -> str:
    lines = content.splitlines()
    if line is None:
        return "\n".join(lines[:40])
    lo, hi = max(0, line - 1 - radius), min(len(lines), line + radius)
    return "\n".join(f"{i + 1}: {text}" for i, text in enumerate(lines[lo:hi], start=lo))


def run_llm_verification(
    tool_findings: list[ToolFinding],
    enforcement_findings: list[EnforcementFinding],
    repo_root: str | None = None,
    model: str = "sonnet",
    token_budget: int = 10000,
) -> tuple[list[ToolFinding], list[EnforcementFinding], list[str]]:
    errors: list[str] = []
    try:
        client = _get_anthropic_client()
    except (ImportError, ValueError) as e:
        return tool_findings, enforcement_findings, [f"llm-verify unavailable: {e}"]

    model_id = MODEL_IDS.get(model, MODEL_IDS["sonnet"])
    spent = 0

    def verify(finding, rule_key: str):
        nonlocal spent
        if finding.suppressed:
            return finding
        if spent >= token_budget:
            return finding
        path, line, _ = _split_location(finding.location)
        full = os.path.join(repo_root, path) if repo_root else path
        try:
            with open(full, encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return finding
        prompt = (
            f"Finding: [{rule_key}] {finding.message}\n"
            f"Location: {finding.location}\n\n"
            f"File context:\n{_context_snippet(content, line)}\n"
        )
        try:
            response = client.messages.create(
                model=model_id,
                max_tokens=1024,
                system=_SYSTEM,
                output_config={"format": _VERDICT_SCHEMA},
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:  # crucible-ignore: no-catch-exception -- fail-open boundary: API failures must never hide findings
            errors.append(f"llm-verify API error: {e}")
            spent = token_budget  # stop trying
            return finding
        spent += response.usage.input_tokens + response.usage.output_tokens
        if spent >= token_budget:
            errors.append(f"llm-verify budget exhausted ({spent}/{token_budget})")
        try:
            verdict = json.loads(response.content[0].text)
        except (ValueError, IndexError, AttributeError):
            return finding
        if not verdict.get("suppress"):
            return finding
        reason = str(verdict.get("counterargument", ""))[:200]
        return dataclasses.replace(
            finding, suppressed=True, suppression_reason=f"llm:{model} — {reason}")

    verified_tools = [verify(f, f"{f.tool}/{f.rule}") for f in tool_findings]
    verified_enf = [verify(f, f.assertion_id) for f in enforcement_findings]
    return verified_tools, verified_enf, errors
```

Check `MODEL_IDS` is the actual constant name in `compliance.py` (`grep -n "MODEL_IDS\|sonnet.*claude" src/crucible/enforcement/compliance.py`) — if the dict has a different name, import that name and keep this module's references consistent.

- [ ] **Step 4: Wire the CLI flag** — in `cli.py`'s review argument registration: `review_parser.add_argument("--verify-llm", action="store_true", help="LLM-verify findings the deterministic tier could not decide (costs tokens)")`. In both review paths, after the deterministic `run_verification` call:

```python
    if getattr(args, "verify_llm", False):
        from crucible.verify.llm import run_llm_verification
        all_findings, enforcement_findings, llm_errors = run_llm_verification(
            all_findings, enforcement_findings, repo_root=repo_root_or_none)
        errors.extend(llm_errors)
```

- [ ] **Step 5: Wire the MCP review param** — the spec makes the LLM tier available on both review surfaces. In `server.py`, add an optional `verify_llm: bool = False` parameter to the `review` tool signature (follow the existing optional-parameter style of that tool) and, after the deterministic `run_verification` call added in Task 9:

```python
        if verify_llm:
            from crucible.verify.llm import run_llm_verification
            all_findings, enforcement_findings, llm_errors = run_llm_verification(
                all_findings, enforcement_findings)
            errors.extend(llm_errors)
```

Append to `tests/test_server.py` a test that patches `crucible.verify.llm._get_anthropic_client` with the `_mock_client(True)` stub from `tests/test_verify_llm.py` (copy the helper into the test), invokes the review tool with `verify_llm=True` on a file yielding one unbound finding, and asserts it lands in the Suppressed section.

- [ ] **Step 6: Run to verify it passes** — `python -m pytest tests/test_verify_llm.py tests/test_cli.py tests/test_server.py -q` → PASS. `ruff check src/`.
- [ ] **Step 7: Export** — add `run_llm_verification` to `crucible/verify/__init__.py` imports and `__all__`.
- [ ] **Step 8: Commit** — `git add src/crucible/verify tests/test_verify_llm.py src/crucible/cli.py src/crucible/server.py tests/test_server.py && git commit -m "feat: opt-in LLM verification tier"`

---

### Task 12: Verification sweep + docs + wrap-up

**Files:**
- Modify: `docs/v2/phase6_verifier_corpus.md` (append measurement note), `CLAUDE.md` (one line in the CLI list)
- No new production code.

- [ ] **Step 1: Full suite** — `python -m pytest -q` → 7 known env-broken integration failures only; everything else PASS. Count must be ≥ previous (769) + all new tests.
- [ ] **Step 2: Wheel check** — `rm -rf dist build && python -m build --wheel && unzip -l dist/*.whl | grep -E "verify/|verifiers.yaml"` → `crucible/verify/*.py` and `crucible/verify/bundled/verifiers.yaml` all present. Then `rm -rf dist build`.
- [ ] **Step 3: Fresh clone** — clone the repo to the scratchpad, `python -m venv .venv && .venv/bin/pip install -e ".[dev]"`, run `.venv/bin/python -m pytest -q --ignore=tests/test_integration.py` → all pass.
- [ ] **Step 4: Live corpus measurement** — in the real repo: `crucible review src/crucible/cli.py --no-git` and confirm the Group 1/2 corpus findings land in "Suppressed by verifier". Append to `docs/v2/phase6_verifier_corpus.md`:

```markdown
## Phase 6 landed (measurement)

`crucible review src/crucible/cli.py` now suppresses the Group 1/2
findings via the deterministic verifier (observed <date>); the enforced
gate `tests/test_verifier_corpus.py` holds the full 125/125 plus a
true-positive control group. New FP classes: add a predicate + binding +
corpus entry, and extend the gate.
```

- [ ] **Step 5: CLAUDE.md** — in the CLI commands block, after the `crucible review` lines add: `crucible review --no-verify           # Raw findings (skip FP verifier)`.
- [ ] **Step 6: Commit** — `git add docs/v2/phase6_verifier_corpus.md CLAUDE.md && git commit -m "docs: Phase 6 verifier landed — corpus measurement + CLI note"`
- [ ] **Step 7: Update the project memory** (`~/.claude/projects/-Users-be-nvy-crucible/memory/project_crucible_v2_progress.md`): Phase 6 done (commits + test counts), Phase 7 next, any new conventions discovered.
