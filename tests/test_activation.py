"""Tests for activation energy features (session context injection)."""

import json
from pathlib import Path
from unittest.mock import patch

from crucible.history import (
    clear_recent_findings,
    load_recent_findings,
    save_recent_findings,
)
from crucible.hooks.claudecode import (
    _generate_enforcement_summary,
    generate_settings_json,
    generate_system_templates,
    run_session_hook,
)


class TestHistoryModule:
    """Tests for crucible.history module."""

    def test_save_recent_findings_creates_file(self, tmp_path: Path) -> None:
        """Test that save_recent_findings creates the history file."""
        from crucible.enforcement.models import EnforcementFinding, Priority

        findings = [
            EnforcementFinding(
                assertion_id="no-eval",
                message="eval() is dangerous",
                severity="error",
                priority=Priority.CRITICAL,
                location="test.py:10:5",
                match_text="eval(user_input)",
            )
        ]

        result = save_recent_findings(findings, "src/test.py", str(tmp_path))

        assert result is not None
        assert result.exists()
        content = result.read_text()
        assert "Last Review" in content
        assert "no-eval" in content
        assert "eval() is dangerous" in content

    def test_save_recent_findings_clears_when_no_findings(self, tmp_path: Path) -> None:
        """Test that save_recent_findings removes file when no active findings."""
        # Create a findings file first
        history_dir = tmp_path / ".crucible" / "history"
        history_dir.mkdir(parents=True)
        recent_file = history_dir / "recent-findings.md"
        recent_file.write_text("# Old findings")

        # Save empty findings
        result = save_recent_findings([], "src/test.py", str(tmp_path))

        assert result is None
        assert not recent_file.exists()

    def test_save_recent_findings_excludes_suppressed(self, tmp_path: Path) -> None:
        """Test that suppressed findings are not saved."""
        from crucible.enforcement.models import EnforcementFinding, Priority

        findings = [
            EnforcementFinding(
                assertion_id="no-eval",
                message="eval() is dangerous",
                severity="error",
                priority=Priority.CRITICAL,
                location="test.py:10:5",
                suppressed=True,
                suppression_reason="intentional",
            )
        ]

        result = save_recent_findings(findings, "src/test.py", str(tmp_path))

        # Should clear/not create file since all findings are suppressed
        assert result is None

    def test_load_recent_findings_returns_content(self, tmp_path: Path) -> None:
        """Test loading recent findings content."""
        history_dir = tmp_path / ".crucible" / "history"
        history_dir.mkdir(parents=True)
        recent_file = history_dir / "recent-findings.md"
        recent_file.write_text("# Last Review\n\nSome findings here")

        content = load_recent_findings(str(tmp_path))

        assert content is not None
        assert "Last Review" in content

    def test_load_recent_findings_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Test that loading returns None when file doesn't exist."""
        content = load_recent_findings(str(tmp_path))
        assert content is None

    def test_clear_recent_findings(self, tmp_path: Path) -> None:
        """Test clearing recent findings."""
        history_dir = tmp_path / ".crucible" / "history"
        history_dir.mkdir(parents=True)
        recent_file = history_dir / "recent-findings.md"
        recent_file.write_text("# Old findings")

        result = clear_recent_findings(str(tmp_path))

        assert result is True
        assert not recent_file.exists()

    def test_clear_recent_findings_returns_false_when_missing(
        self, tmp_path: Path
    ) -> None:
        """Test that clear returns False when file doesn't exist."""
        result = clear_recent_findings(str(tmp_path))
        assert result is False


class TestEnforcementSummary:
    """Tests for enforcement summary generation."""

    def test_generate_enforcement_summary_basic(self) -> None:
        """Test basic enforcement summary generation."""
        from crucible.enforcement.models import Assertion, AssertionType, Priority

        assertions = [
            Assertion(
                id="no-eval",
                type=AssertionType.PATTERN,
                message="eval() is dangerous",
                severity="error",
                priority=Priority.CRITICAL,
                pattern=r"\beval\s*\(",
            ),
            Assertion(
                id="no-exec",
                type=AssertionType.PATTERN,
                message="exec() allows arbitrary code",
                severity="error",
                priority=Priority.CRITICAL,
                pattern=r"\bexec\s*\(",
            ),
            Assertion(
                id="no-md5",
                type=AssertionType.PATTERN,
                message="Use SHA-256 instead of MD5",
                severity="warning",
                priority=Priority.MEDIUM,
                pattern=r"md5\(",
            ),
        ]

        summary = _generate_enforcement_summary(assertions)

        assert "Crucible Enforcement Active" in summary
        assert "Critical Priority" in summary
        assert "no-eval" in summary
        assert "no-exec" in summary
        assert "Medium Priority" in summary
        assert "no-md5" in summary

    def test_generate_enforcement_summary_excludes_prewrite(self) -> None:
        """Test that prewrite-only assertions are excluded."""
        from crucible.enforcement.models import Assertion, AssertionType, Priority

        assertions = [
            Assertion(
                id="code-assertion",
                type=AssertionType.PATTERN,
                message="Code pattern",
                severity="error",
                priority=Priority.HIGH,
                pattern=r"pattern",
                scope="code",
            ),
            Assertion(
                id="prewrite-assertion",
                type=AssertionType.LLM,
                message="Prewrite check",
                severity="error",
                priority=Priority.HIGH,
                scope="prewrite",
            ),
        ]

        summary = _generate_enforcement_summary(assertions)

        assert "code-assertion" in summary
        assert "prewrite-assertion" not in summary


class TestSessionHook:
    """Tests for SessionStart hook."""

    def test_run_session_hook_returns_json(self, tmp_path: Path) -> None:
        """Test that session hook returns valid JSON output."""
        # Create a mock assertion file
        assertions_dir = tmp_path / ".crucible" / "assertions"
        assertions_dir.mkdir(parents=True)
        (assertions_dir / "test.yaml").write_text("""
version: "0.5"
name: Test
description: Test assertions
assertions:
  - id: test-rule
    type: pattern
    pattern: "test_pattern"
    message: Test message
    severity: error
    priority: high
""")

        input_data = json.dumps({"cwd": str(tmp_path)})

        with patch("crucible.hooks.claudecode.load_assertions") as mock_load:
            from crucible.enforcement.models import Assertion, AssertionType, Priority

            mock_load.return_value = (
                [
                    Assertion(
                        id="test-rule",
                        type=AssertionType.PATTERN,
                        message="Test message",
                        severity="error",
                        priority=Priority.HIGH,
                        pattern="test",
                    )
                ],
                [],
            )

            # Capture stdout
            import io
            import sys

            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured

            try:
                exit_code = run_session_hook(input_data)
            finally:
                sys.stdout = old_stdout

            output = captured.getvalue()

        assert exit_code == 0
        if output.strip():
            data = json.loads(output)
            assert "hookSpecificOutput" in data
            assert data["hookSpecificOutput"]["hookEventName"] == "SessionStart"
            assert "additionalContext" in data["hookSpecificOutput"]

    def test_run_session_hook_includes_system_files(self, tmp_path: Path) -> None:
        """Test that session hook includes .crucible/system/*.md files."""
        system_dir = tmp_path / ".crucible" / "system"
        system_dir.mkdir(parents=True)
        (system_dir / "team-patterns.md").write_text("# Team Patterns\n\nOur conventions")

        input_data = json.dumps({"cwd": str(tmp_path)})

        with patch("crucible.hooks.claudecode.load_assertions") as mock_load:
            mock_load.return_value = ([], [])

            import io
            import sys

            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured

            try:
                run_session_hook(input_data)
            finally:
                sys.stdout = old_stdout

            output = captured.getvalue()

        if output.strip():
            data = json.loads(output)
            context = data["hookSpecificOutput"]["additionalContext"]
            assert "Team Patterns" in context
            assert "Our conventions" in context

    def test_run_session_hook_includes_recent_findings(self, tmp_path: Path) -> None:
        """Test that session hook includes recent findings."""
        history_dir = tmp_path / ".crucible" / "history"
        history_dir.mkdir(parents=True)
        (history_dir / "recent-findings.md").write_text(
            "# Last Review\n\n## ERROR (1)\n- **no-eval**: Found eval()"
        )

        input_data = json.dumps({"cwd": str(tmp_path)})

        with patch("crucible.hooks.claudecode.load_assertions") as mock_load:
            mock_load.return_value = ([], [])

            import io
            import sys

            captured = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = captured

            try:
                run_session_hook(input_data)
            finally:
                sys.stdout = old_stdout

            output = captured.getvalue()

        if output.strip():
            data = json.loads(output)
            context = data["hookSpecificOutput"]["additionalContext"]
            assert "Last Review" in context
            assert "no-eval" in context


class TestSettingsGenerator:
    """Tests for settings.json generation."""

    def test_generate_settings_json_adds_session_start_hook(
        self, tmp_path: Path
    ) -> None:
        """Test that SessionStart hook is added to settings."""
        settings_path = generate_settings_json(str(tmp_path))

        with open(settings_path) as f:
            settings = json.load(f)

        assert "hooks" in settings
        assert "SessionStart" in settings["hooks"]

        session_hooks = settings["hooks"]["SessionStart"]
        assert len(session_hooks) >= 1

        # Find the crucible session hook
        crucible_hook = None
        for hook in session_hooks:
            if isinstance(hook, dict) and "hooks" in hook:
                for h in hook["hooks"]:
                    if "crucible hooks claudecode session" in h.get("command", ""):
                        crucible_hook = hook
                        break

        assert crucible_hook is not None
        assert crucible_hook["matcher"] == "startup|resume"

    def test_generate_settings_json_preserves_existing(self, tmp_path: Path) -> None:
        """Test that existing settings are preserved."""
        # Create existing settings
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        existing = {
            "customSetting": "value",
            "hooks": {
                "PreToolUse": [{"matcher": "custom", "hooks": []}]
            }
        }
        (claude_dir / "settings.json").write_text(json.dumps(existing))

        settings_path = generate_settings_json(str(tmp_path))

        with open(settings_path) as f:
            settings = json.load(f)

        assert settings["customSetting"] == "value"
        assert "PreToolUse" in settings["hooks"]
        assert "PostToolUse" in settings["hooks"]
        assert "SessionStart" in settings["hooks"]


class TestSystemTemplates:
    """Tests for system template generation."""

    def test_generate_system_templates_creates_files(self, tmp_path: Path) -> None:
        """Test that system templates are created."""
        created = generate_system_templates(str(tmp_path))

        assert len(created) == 2
        assert (tmp_path / ".crucible" / "system" / "team-patterns.md").exists()
        assert (tmp_path / ".crucible" / "system" / "focus.md").exists()

    def test_generate_system_templates_does_not_overwrite(
        self, tmp_path: Path
    ) -> None:
        """Test that existing files are not overwritten."""
        system_dir = tmp_path / ".crucible" / "system"
        system_dir.mkdir(parents=True)
        existing_content = "# My Custom Content"
        (system_dir / "team-patterns.md").write_text(existing_content)

        created = generate_system_templates(str(tmp_path))

        # Only focus.md should be created
        assert len(created) == 1
        assert "focus.md" in created[0]

        # Verify existing file wasn't modified
        content = (system_dir / "team-patterns.md").read_text()
        assert content == existing_content
