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
