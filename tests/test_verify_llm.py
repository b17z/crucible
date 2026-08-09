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
