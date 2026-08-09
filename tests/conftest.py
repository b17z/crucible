"""Shared test configuration.

The suite must never reach the live Anthropic API: a developer machine
with credentials (env var or ~/.config/crucible/secrets.yaml) would
otherwise make real model calls from any test that leaves LLM compliance
enabled — slow, token-burning, and nondeterministic. These patches force
the no-credentials fail-open path everywhere; tests that need an API
response mock `_get_anthropic_client` themselves (their patch nests
inside this one and restores cleanly).
"""

import pytest


def _no_client() -> None:
    raise ValueError("live Anthropic API calls are disabled in tests")


@pytest.fixture(autouse=True)
def _no_live_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(
        "crucible.enforcement.compliance._load_api_key_from_config", lambda: None
    )
    monkeypatch.setattr(
        "crucible.enforcement.compliance._get_anthropic_client", _no_client
    )
