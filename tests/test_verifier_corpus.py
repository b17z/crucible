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
