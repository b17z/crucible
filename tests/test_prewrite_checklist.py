"""Tests for `crucible prewrite review --checklist` and honest exit codes.

Covers: selection sharing between the API and checklist paths, the
checklist render format (spec section 2, verbatim), the no-anthropic-import
guarantee on the checklist path, and the exit-code fix for keyless/partial/
full API runs.
"""

import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent
DELIVERY_LOOP_SKILL_PATH = (
    REPO_ROOT / "src" / "crucible" / "skills" / "meta" / "delivery-loop" / "SKILL.md"
)
PORTABILITY_PATH = REPO_ROOT / "docs" / "PORTABILITY.md"
BUILD_ALONG_PATH = REPO_ROOT / "docs" / "BUILD-ALONG.md"

from crucible.cli import cmd_prewrite_review
from crucible.prewrite.models import PrewriteFinding
from crucible.prewrite.review import (
    PrewriteCheck,
    checks_from_assertions,
    render_prewrite_checklist,
    select_prewrite_checks,
)

FIXTURE_SPEC = """# Feature PRD

## Problem Statement

This is the problem we're solving.

## User Stories

- As a user, I want...

## Success Metrics

How we measure success.
"""


def _make_namespace(path: str, **overrides: object) -> Namespace:
    """Build a Namespace with every attribute cmd_prewrite_review reads."""
    base: dict[str, object] = {
        "path": path,
        "template": None,
        "skills": None,
        "checklist": False,
        "json": False,
        "fail_on": None,
        "model": None,
        "token_budget": None,
    }
    base.update(overrides)
    return Namespace(**base)


@pytest.fixture
def spec_file(tmp_path: Path) -> Path:
    p = tmp_path / "spec.md"
    p.write_text(FIXTURE_SPEC)
    return p


class TestSelectPrewriteChecks:
    """The shared selection function both paths call."""

    def test_selects_all_bundled_prewrite_llm_assertions(self, spec_file: Path) -> None:
        selection = select_prewrite_checks(str(spec_file))
        assert selection.errors == []
        assert len(selection.assertions) >= 8
        ids = {a.id for a in selection.assertions}
        assert "spec-missing-auth" in ids
        assert "spec-no-success-criteria" in ids

    def test_read_failure_returns_empty_with_error(self, tmp_path: Path) -> None:
        missing = tmp_path / "nope.md"
        selection = select_prewrite_checks(str(missing))
        assert selection.assertions == []
        assert selection.content == ""
        assert any("Failed to read file" in e for e in selection.errors)
        assert selection.read_error is not None
        assert "Failed to read file" in selection.read_error

    def test_empty_file_is_not_a_read_failure(self, tmp_path: Path) -> None:
        """A 0-byte file reads successfully — it's an empty document, not a
        read error. It must proceed to evaluation like any other spec."""
        empty = tmp_path / "empty.md"
        empty.write_text("")
        selection = select_prewrite_checks(str(empty))
        assert selection.read_error is None
        assert selection.content == ""
        assert len(selection.assertions) >= 8

    def test_explicit_template_skips_detection(self, spec_file: Path) -> None:
        selection = select_prewrite_checks(str(spec_file), template="tdd")
        assert selection.template == "tdd"


class TestChecksFromAssertions:
    def test_skips_assertions_without_compliance(self, spec_file: Path) -> None:
        selection = select_prewrite_checks(str(spec_file))
        checks = checks_from_assertions(selection.assertions)
        # every real bundled prewrite assertion carries compliance text
        assert len(checks) == len(selection.assertions)
        for check in checks:
            assert check.criteria


class TestRenderPrewriteChecklist:
    """Format is verbatim from spec section 2."""

    def test_header_and_instruction_present(self) -> None:
        checks = [PrewriteCheck(id="a1", severity="error", criteria="Do the thing.")]
        rendered = render_prewrite_checklist("spec.md", "prd", checks)

        assert rendered.startswith("# Pre-Write Review Checklist\n")
        assert "Spec: spec.md (template: prd)" in rendered
        assert "Evaluate the document against each check below." in rendered
        assert "## Checks" in rendered

    def test_one_block_per_check_verbatim(self) -> None:
        checks = [
            PrewriteCheck(id="chk-one", severity="error", criteria="Criteria one text."),
            PrewriteCheck(id="chk-two", severity="info", criteria="Criteria two text."),
        ]
        rendered = render_prewrite_checklist("spec.md", "prd", checks)

        assert "### chk-one — severity: error" in rendered
        assert "Criteria one text." in rendered
        assert "### chk-two — severity: info" in rendered
        assert "Criteria two text." in rendered
        # order preserved
        assert rendered.index("chk-one") < rendered.index("chk-two")

    def test_none_template_renders_as_none_label(self) -> None:
        rendered = render_prewrite_checklist("spec.md", None, [])
        assert "(template: none)" in rendered


class TestChecklistCliRender:
    """`--checklist` on a real spec: renders every applicable check, exits 0."""

    def test_checklist_renders_and_exits_zero(self, spec_file: Path, capsys: pytest.CaptureFixture) -> None:
        args = _make_namespace(str(spec_file), checklist=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "# Pre-Write Review Checklist" in out
        assert "## Checks" in out

        selection = select_prewrite_checks(str(spec_file))
        for assertion in selection.assertions:
            assert f"### {assertion.id} — severity: {assertion.severity}" in out
            assert assertion.compliance in out

    def test_checklist_json_shape(self, spec_file: Path, capsys: pytest.CaptureFixture) -> None:
        import json

        args = _make_namespace(str(spec_file), checklist=True, json=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)

        assert set(payload.keys()) == {"path", "template", "mode", "checks"}
        assert payload["path"] == str(spec_file)
        assert payload["mode"] == "checklist"
        assert isinstance(payload["checks"], list)
        assert payload["checks"], "expected at least one check"
        for check in payload["checks"]:
            assert set(check.keys()) == {"id", "severity", "criteria"}

    def test_checklist_requires_no_anthropic_import(
        self, spec_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The checklist path must not import `anthropic` at all."""

        class _PoisonedModule:
            def __getattr__(self, name: str) -> object:
                raise AssertionError(
                    f"checklist path touched anthropic.{name} — it must not import anthropic"
                )

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "crucible.enforcement.compliance._load_api_key_from_config", lambda: None
        )
        monkeypatch.setitem(sys.modules, "anthropic", _PoisonedModule())

        args = _make_namespace(str(spec_file), checklist=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 0


class TestChecklistErrorHandling:
    """Finding 2: `--checklist` must not swallow `selection.errors`."""

    def test_directory_path_exits_one_with_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """A directory arg passes the exists() check in cmd_prewrite_review
        but can't be read as a spec — must not render an empty checklist
        with exit 0."""
        args = _make_namespace(str(tmp_path), checklist=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "## Checks" not in captured.out
        assert captured.err.strip() != ""

    def test_directory_path_json_exits_one_with_error(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        args = _make_namespace(str(tmp_path), checklist=True, json=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        # No JSON is emitted when nothing could be rendered at all.
        assert captured.err.strip() != ""

    def test_errors_with_some_checks_surface_on_stderr_and_exit_zero(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Partial failure: some checks still rendered, so the render
        succeeded overall (exit 0), but the error must not vanish."""
        from crucible.prewrite.review import PrewriteSelection

        real_selection = select_prewrite_checks(str(spec_file))
        assert real_selection.assertions, "fixture must yield at least one check"

        partial_selection = PrewriteSelection(
            content=real_selection.content,
            template=real_selection.template,
            checklist=real_selection.checklist,
            knowledge_to_load=real_selection.knowledge_to_load,
            skills_loaded=real_selection.skills_loaded,
            assertions=real_selection.assertions,
            errors=["broken-assertions.yaml: invalid YAML"],
        )

        with patch(
            "crucible.prewrite.review.select_prewrite_checks",
            return_value=partial_selection,
        ):
            args = _make_namespace(str(spec_file), checklist=True)
            exit_code = cmd_prewrite_review(args)

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "## Checks" in captured.out
        assert "broken-assertions.yaml" in captured.err

    def test_errors_with_some_checks_json_includes_errors_key(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import json

        from crucible.prewrite.review import PrewriteSelection

        real_selection = select_prewrite_checks(str(spec_file))
        partial_selection = PrewriteSelection(
            content=real_selection.content,
            template=real_selection.template,
            checklist=real_selection.checklist,
            knowledge_to_load=real_selection.knowledge_to_load,
            skills_loaded=real_selection.skills_loaded,
            assertions=real_selection.assertions,
            errors=["broken-assertions.yaml: invalid YAML"],
        )

        with patch(
            "crucible.prewrite.review.select_prewrite_checks",
            return_value=partial_selection,
        ):
            args = _make_namespace(str(spec_file), checklist=True, json=True)
            exit_code = cmd_prewrite_review(args)

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert "errors" in payload
        assert payload["errors"] == ["broken-assertions.yaml: invalid YAML"]
        assert payload["checks"], "expected checks to still render"


class TestApiPathExitCodes:
    """Exit-code fix: honest exits when nothing evaluated, partial, full."""

    def test_keyless_api_run_exits_one_with_pointer(
        self, spec_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "crucible.enforcement.compliance._load_api_key_from_config", lambda: None
        )

        args = _make_namespace(str(spec_file))
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "--checklist" in captured.err
        assert "PASSED" not in captured.out

    def test_keyless_fail_on_info_still_exits_one(
        self, spec_file: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr(
            "crucible.enforcement.compliance._load_api_key_from_config", lambda: None
        )

        args = _make_namespace(str(spec_file), fail_on="info")
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        assert "--checklist" in capsys.readouterr().err

    def test_partial_error_warns_and_exits_on_findings(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """One assertion errors, one evaluates clean with no findings -> pass."""
        call_count = {"n": 0}

        def fake_run(assertion_id, compliance_text, content, severity, model="sonnet"):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return [], 0, "simulated API error"
            return [], 5, None

        with patch("crucible.prewrite.review._run_prewrite_assertion", side_effect=fake_run):
            args = _make_namespace(str(spec_file))
            exit_code = cmd_prewrite_review(args)

        err = capsys.readouterr().err
        assert "partial evaluation" in err
        assert "⚠" in err
        assert exit_code == 0

    def test_full_pass_exit_unchanged(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        def fake_run(assertion_id, compliance_text, content, severity, model="sonnet"):
            return [], 5, None

        with patch("crucible.prewrite.review._run_prewrite_assertion", side_effect=fake_run):
            args = _make_namespace(str(spec_file))
            exit_code = cmd_prewrite_review(args)

        captured = capsys.readouterr()
        assert "partial evaluation" not in captured.out
        assert "partial evaluation" not in captured.err
        assert exit_code == 0

    def test_full_fail_exit_unchanged(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        def fake_run(assertion_id, compliance_text, content, severity, model="sonnet"):
            return (
                [PrewriteFinding(assertion_id=assertion_id, message="bad", severity="error")],
                5,
                None,
            )

        with patch("crucible.prewrite.review._run_prewrite_assertion", side_effect=fake_run):
            args = _make_namespace(str(spec_file))
            exit_code = cmd_prewrite_review(args)

        captured = capsys.readouterr()
        assert "partial evaluation" not in captured.out
        assert "partial evaluation" not in captured.err
        assert exit_code == 1

    def test_api_json_output_gains_evaluated_count(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import json

        def fake_run(assertion_id, compliance_text, content, severity, model="sonnet"):
            return [], 5, None

        with patch("crucible.prewrite.review._run_prewrite_assertion", side_effect=fake_run):
            args = _make_namespace(str(spec_file), json=True)
            exit_code = cmd_prewrite_review(args)

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        assert "evaluated" in payload
        assert payload["evaluated"] == payload_expected_count(str(spec_file))

    def test_keyless_json_stdout_is_valid_json(
        self, spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """The honest-exit pointer must not corrupt --json stdout."""
        import json

        args = _make_namespace(str(spec_file), json=True)
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        payload = json.loads(captured.out)  # raises if pointer leaked into stdout
        assert payload["evaluated"] == 0
        assert "--checklist" in captured.err


def payload_expected_count(spec_path: str) -> int:
    selection = select_prewrite_checks(spec_path)
    return len(checks_from_assertions(selection.assertions))


class TestEmptySpecRegression:
    """Finding 1: a 0-byte spec must be evaluated, not silently PASSED."""

    @pytest.fixture
    def empty_spec_file(self, tmp_path: Path) -> Path:
        p = tmp_path / "empty.md"
        p.write_text("")
        return p

    def test_empty_file_with_mocked_runner_invokes_assertions(
        self, empty_spec_file: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With a key present, assertions actually run against the empty
        document instead of short-circuiting on empty content."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")

        call_count = {"n": 0}

        def fake_run(assertion_id, compliance_text, content, severity, model="sonnet"):
            call_count["n"] += 1
            assert content == ""
            return [], 5, None

        with patch("crucible.prewrite.review._run_prewrite_assertion", side_effect=fake_run):
            args = _make_namespace(str(empty_spec_file))
            exit_code = cmd_prewrite_review(args)

        assert call_count["n"] > 0
        assert exit_code == 0

    def test_empty_file_keyless_is_honest_exit_not_passed(
        self, empty_spec_file: Path, capsys: pytest.CaptureFixture
    ) -> None:
        """Keyless + empty file: every assertion errors (no key), so this
        is the nothing-evaluated honest exit — not a silent PASSED/exit 0."""
        args = _make_namespace(str(empty_spec_file))
        exit_code = cmd_prewrite_review(args)

        assert exit_code == 1
        captured = capsys.readouterr()
        assert "PASSED" not in captured.out
        assert "--checklist" in captured.err


class TestChecklistDocsWiring:
    """Spec §4: the four doc surfaces name --checklist."""

    def test_delivery_loop_skill_names_checklist(self) -> None:
        text = DELIVERY_LOOP_SKILL_PATH.read_text()
        assert "--checklist" in text

    def test_portability_mentions_checklist(self) -> None:
        text = PORTABILITY_PATH.read_text()
        assert "--checklist" in text

    def test_build_along_kickoff_block_mentions_checklist(self) -> None:
        text = BUILD_ALONG_PATH.read_text()
        fence_start = text.index("```text")
        fence_end = text.index("```", fence_start + len("```text"))
        block = text[fence_start:fence_end]
        assert "--checklist" in block
