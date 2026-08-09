"""Cascade + validation tests for the policy layer."""

from pathlib import Path
from unittest.mock import patch

from crucible.policy import load_policies, validate_policies


def test_bundled_policies_load_and_validate_clean() -> None:
    policies, errors = load_policies()
    assert errors == []
    assert {p.name for p in policies} == {
        "dependency_quarantine", "settings_integrity", "bash_denylist",
    }
    issues = validate_policies(policies)
    assert [i for i in issues if i.level == "error"] == [], issues


def test_project_overrides_bundled(tmp_path: Path) -> None:
    proj = tmp_path / "policies"
    proj.mkdir()
    (proj / "custom.yaml").write_text(
        "name: bash_denylist\ndescription: project override\nseverity: low\n"
    )
    with patch("crucible.policy.validator.POLICIES_PROJECT", proj):
        policies, errors = load_policies()
    assert errors == []
    named = {p.name: p for p in policies}
    assert named["bash_denylist"].severity == "low"
    assert named["bash_denylist"].description == "project override"


def test_parse_error_reported_not_raised(tmp_path: Path) -> None:
    proj = tmp_path / "policies"
    proj.mkdir()
    (proj / "broken.yaml").write_text("{ not yaml [")
    with patch("crucible.policy.validator.POLICIES_PROJECT", proj):
        policies, errors = load_policies()
    assert len(errors) == 1
    assert len(policies) == 3  # bundled still load


def test_missing_handler_is_error(tmp_path: Path) -> None:
    proj = tmp_path / "policies"
    proj.mkdir()
    (proj / "p.yaml").write_text(
        "name: ghost\ndescription: d\nseverity: high\n"
        "hooks:\n  - event: PreToolUse\n    handler: no/such/handler.sh\n"
    )
    with patch("crucible.policy.validator.POLICIES_PROJECT", proj):
        policies, _ = load_policies()
        issues = validate_policies(policies)
    ghost = [i for i in issues if i.policy == "ghost"]
    assert ghost and ghost[0].level == "error"
    assert "handler" in ghost[0].field


def test_unknown_skill_is_warning(tmp_path: Path) -> None:
    proj = tmp_path / "policies"
    proj.mkdir()
    (proj / "p.yaml").write_text(
        "name: skilly\ndescription: d\nseverity: low\n"
        "activated_by:\n  skills:\n    - no-such-skill-anywhere\n"
    )
    with patch("crucible.policy.validator.POLICIES_PROJECT", proj):
        policies, _ = load_policies()
        issues = validate_policies(policies)
    skilly = [i for i in issues if i.policy == "skilly"]
    assert skilly and skilly[0].level == "warning"


def test_watched_files_drift_is_error(tmp_path: Path) -> None:
    proj = tmp_path / "policies"
    proj.mkdir()
    (proj / "si.yaml").write_text(
        "name: settings_integrity\ndescription: drifted\nseverity: critical\n"
        "watched_files:\n  - path: .claude/settings.json\n"
    )
    with patch("crucible.policy.validator.POLICIES_PROJECT", proj):
        policies, _ = load_policies()
        issues = validate_policies(policies)
    drift = [i for i in issues if i.policy == "settings_integrity" and i.level == "error"]
    assert drift, issues
    assert "watched_files" in drift[0].field
