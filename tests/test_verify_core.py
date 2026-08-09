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
