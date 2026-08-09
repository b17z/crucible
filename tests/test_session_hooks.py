"""Tests for the Phase 4 SessionStart extensions in claudecode.py.

Covers the three additions: Tier-1 skill discovery injection, the
settings-integrity note, and the active-policy note. Hermetic where
possible; the discovery/policy bits read the bundled tree (stable).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from crucible.hooks.claudecode import (
    _session_integrity_note,
    _session_policy_note,
    run_session_hook,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestIntegrityNote:
    def test_none_when_no_baselines(self, tmp_path: Path) -> None:
        (tmp_path / ".crucible").mkdir()
        assert _session_integrity_note(tmp_path) is None

    def test_none_when_baselines_match(self, tmp_path: Path) -> None:
        bl = tmp_path / ".crucible" / "baselines"
        bl.mkdir(parents=True)
        claude = tmp_path / ".claude"
        claude.mkdir()
        settings = claude / "settings.json"
        settings.write_text('{"ok": 1}')
        (bl / "settings.sha256").write_text(_sha256(settings))
        (bl / "mcp.sha256").write_text("MISSING")
        (bl / "extensions.sha256").write_text("MISSING")
        assert _session_integrity_note(tmp_path) is None

    def test_warns_on_divergence(self, tmp_path: Path) -> None:
        bl = tmp_path / ".crucible" / "baselines"
        bl.mkdir(parents=True)
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text('{"tampered": 1}')
        (bl / "settings.sha256").write_text("wronghash")
        (bl / "mcp.sha256").write_text("MISSING")
        (bl / "extensions.sha256").write_text("MISSING")
        note = _session_integrity_note(tmp_path)
        assert note is not None
        assert "settings" in note
        assert "integrity" in note.lower()

    def test_warns_on_missing_baseline(self, tmp_path: Path) -> None:
        bl = tmp_path / ".crucible" / "baselines"
        bl.mkdir(parents=True)
        # baselines dir exists but no settings.sha256 → suspicious
        (bl / "mcp.sha256").write_text("MISSING")
        note = _session_integrity_note(tmp_path)
        assert note is not None
        assert "missing" in note.lower()


class TestBaselineSnapshots:
    def test_init_writes_snapshots(self, tmp_path: Path, monkeypatch) -> None:
        from crucible.baselines import init_baselines

        monkeypatch.chdir(tmp_path)
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "settings.json").write_text('{"hooks": {}}')

        result = init_baselines()
        assert result.is_ok

        bl = tmp_path / ".crucible" / "baselines"
        assert (bl / "settings.snapshot").read_text() == '{"hooks": {}}'
        # Absent watched files get no snapshot
        assert not (bl / "mcp.snapshot").exists()
        assert not (bl / "extensions.snapshot").exists()

    def test_force_reinit_refreshes_and_prunes(self, tmp_path: Path, monkeypatch) -> None:
        from crucible.baselines import init_baselines

        monkeypatch.chdir(tmp_path)
        (tmp_path / ".mcp.json").write_text('{"mcpServers": {}}')
        assert init_baselines().is_ok

        bl = tmp_path / ".crucible" / "baselines"
        assert (bl / "mcp.snapshot").exists()

        # Watched file removed → force re-init prunes the stale snapshot
        (tmp_path / ".mcp.json").unlink()
        assert init_baselines(force=True).is_ok
        assert not (bl / "mcp.snapshot").exists()


class TestPolicyNote:
    def test_lists_bundled_policies(self) -> None:
        note = _session_policy_note()
        # The bundled tree ships settings_integrity + dependency_quarantine.
        assert note is not None
        assert "settings_integrity" in note
        assert "dependency_quarantine" in note


class TestSessionHookEndToEnd:
    def test_injects_discovery_and_policies(self, tmp_path: Path) -> None:
        (tmp_path / ".crucible").mkdir()
        stdin = json.dumps({"cwd": str(tmp_path)})
        # run_session_hook prints JSON to stdout; capture via capsys-free
        # approach by calling it and re-parsing is awkward, so we just
        # assert it returns 0 and produces parseable output.
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = run_session_hook(stdin)
        assert rc == 0
        out = buf.getvalue().strip()
        assert out, "session hook produced no output"
        parsed = json.loads(out)
        ctx = parsed["hookSpecificOutput"]["additionalContext"]
        assert "Available skills" in ctx  # Tier 1 discovery
        assert "Active policies" in ctx
