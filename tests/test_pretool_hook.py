"""Tests for the PreToolUse Edit/Write assertion pre-check hook."""

import json
from pathlib import Path
from unittest.mock import patch

from crucible.hooks.claudecode import run_pretool_hook


def _assertions_dir(tmp_path: Path) -> Path:
    assertions_dir = tmp_path / ".crucible" / "assertions"
    assertions_dir.mkdir(parents=True)
    (assertions_dir / "rules.yaml").write_text("""
assertions:
  - id: no-eval
    type: pattern
    pattern: "\\\\beval\\\\s*\\\\("
    message: "No eval"
    severity: error
""")
    return assertions_dir


def _run(tmp_path: Path, payload: dict) -> int:
    from crucible.enforcement.assertions import clear_assertion_cache

    clear_assertion_cache()
    payload.setdefault("cwd", str(tmp_path))
    with (
        patch("crucible.enforcement.assertions.ASSERTIONS_PROJECT",
              tmp_path / ".crucible" / "assertions"),
        patch("crucible.enforcement.assertions.ASSERTIONS_USER", tmp_path / "nonexistent"),
        patch("crucible.enforcement.assertions.ASSERTIONS_BUNDLED", tmp_path / "nonexistent"),
    ):
        return run_pretool_hook(json.dumps(payload))


class TestPretoolWrite:
    def test_write_with_violation_denies(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        code = "x = eval('1+1')\n"  # crucible-ignore: no-eval -- fixture text
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "app.py", "content": code},
        })
        assert exit_code == 2

    def test_write_clean_allows(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "app.py", "content": "x = 1\n"},
        })
        assert exit_code == 0

    def test_write_suppressed_violation_allows(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        code = "x = eval('1+1')  # crucible-ignore: no-eval -- known\n"
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "app.py", "content": code},
        })
        assert exit_code == 0


class TestPretoolEdit:
    def test_edit_introducing_violation_denies(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        (tmp_path / "app.py").write_text("x = 1\n")
        code = "x = eval('1+1')\n"  # crucible-ignore: no-eval -- fixture text
        exit_code = _run(tmp_path, {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "app.py",
                "old_string": "x = 1\n",
                "new_string": code,
            },
        })
        assert exit_code == 2

    def test_edit_clean_allows(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        (tmp_path / "app.py").write_text("x = 1\n")
        exit_code = _run(tmp_path, {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "app.py",
                "old_string": "x = 1\n",
                "new_string": "x = 2\n",
            },
        })
        assert exit_code == 0

    def test_edit_leaves_existing_violation_alone(self, tmp_path: Path) -> None:
        """A pre-existing violation elsewhere in the file must not block
        an unrelated edit — only the introduced content is asserted."""
        _assertions_dir(tmp_path)
        legacy = "y = eval('2+2')\nx = 1\n"  # crucible-ignore: no-eval -- fixture text
        (tmp_path / "app.py").write_text(legacy)
        exit_code = _run(tmp_path, {
            "tool_name": "Edit",
            "tool_input": {
                "file_path": "app.py",
                "old_string": "x = 1\n",
                "new_string": "x = 2\n",
            },
        })
        assert exit_code == 0


class TestPretoolConfigAndEdges:
    def test_warn_mode_allows_with_stderr(self, tmp_path: Path, capsys) -> None:
        _assertions_dir(tmp_path)
        (tmp_path / ".crucible" / "claudecode.yaml").write_text("on_finding: warn\n")
        code = "x = eval('1+1')\n"  # crucible-ignore: no-eval -- fixture text
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "app.py", "content": code},
        })
        assert exit_code == 0
        assert "no-eval" in capsys.readouterr().err

    def test_excluded_file_allows(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        (tmp_path / ".crucible" / "claudecode.yaml").write_text(
            'exclude:\n  - "**/*.md"\n'
        )
        code = "eval('1+1')\n"  # crucible-ignore: no-eval -- fixture text
        exit_code = _run(tmp_path, {
            "tool_name": "Write",
            "tool_input": {"file_path": "docs/notes.md", "content": code},
        })
        assert exit_code == 0

    def test_other_tools_ignored(self, tmp_path: Path) -> None:
        _assertions_dir(tmp_path)
        exit_code = _run(tmp_path, {
            "tool_name": "Bash",
            "tool_input": {"command": "echo hi"},
        })
        assert exit_code == 0

    def test_bad_json_allows(self) -> None:
        assert run_pretool_hook("not json {") == 0


class TestPretoolRegistration:
    def test_settings_registers_pretool_hook(self, tmp_path: Path) -> None:
        from crucible.hooks.claudecode import generate_settings_json

        generate_settings_json(str(tmp_path))
        settings_path = generate_settings_json(str(tmp_path))  # idempotent

        with open(settings_path) as f:
            settings = json.load(f)

        pretool = [
            h for h in settings["hooks"]["PreToolUse"]
            if isinstance(h, dict) and h.get("hooks")
            and "crucible hooks claudecode pretool" in h["hooks"][0].get("command", "")
        ]
        assert len(pretool) == 1
        assert pretool[0]["matcher"] == "Edit|Write"


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
