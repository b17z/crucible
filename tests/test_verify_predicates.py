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
