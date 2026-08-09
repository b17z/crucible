"""Schema tests for policy YAML parsing."""

from pathlib import Path

from crucible.policy.schema import SEVERITIES, parse_policy


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "pol.yaml"
    p.write_text(text)
    return p


VALID = """
name: test_policy
description: A test policy.
version: "1.0"
severity: high
hooks:
  - event: PreToolUse
    matcher: Bash
    handler: interfaces/claude_code/pre_tool_use/bash_deny.sh
    blocking: true
    note: exit 2 on match
activated_by:
  skills:
    - security-engineer
recovery:
  - step: investigate
"""


class TestParsePolicy:
    def test_valid_policy_parses(self, tmp_path: Path) -> None:
        result = parse_policy(_write(tmp_path, VALID))
        assert result.is_ok
        p = result.value
        assert p.name == "test_policy"
        assert p.severity == "high"
        assert p.hooks[0].handler.endswith("bash_deny.sh")
        assert p.hooks[0].blocking is True
        assert p.activated_by_skills == ("security-engineer",)
        assert "recovery" in p.extra
        assert p.source_path.endswith("pol.yaml")

    def test_missing_name_errs(self, tmp_path: Path) -> None:
        result = parse_policy(_write(tmp_path, "description: x\nseverity: high\n"))
        assert result.is_err
        assert "name" in result.error

    def test_unknown_severity_errs(self, tmp_path: Path) -> None:
        result = parse_policy(_write(tmp_path, "name: p\ndescription: d\nseverity: apocalyptic\n"))
        assert result.is_err
        assert "severity" in result.error

    def test_malformed_yaml_errs(self, tmp_path: Path) -> None:
        result = parse_policy(_write(tmp_path, "{ not yaml ["))
        assert result.is_err

    def test_hooks_and_skills_optional(self, tmp_path: Path) -> None:
        result = parse_policy(_write(tmp_path, "name: p\ndescription: d\nseverity: low\n"))
        assert result.is_ok
        assert result.value.hooks == ()
        assert result.value.activated_by_skills == ()

    def test_all_bundled_policies_parse(self) -> None:
        bundled = Path("src/crucible/policies")
        results = [parse_policy(p) for p in sorted(bundled.glob("*.yaml"))]
        assert len(results) == 3
        assert all(r.is_ok for r in results), [r.error for r in results if r.is_err]

    def test_severities_constant(self) -> None:
        assert SEVERITIES == ("critical", "high", "medium", "low")
