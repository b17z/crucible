"""Candidate Sign store: write, dedup, list, fail-silent."""

from pathlib import Path

import yaml

from crucible.signs import list_candidates, write_candidate


class TestWriteCandidate:
    def test_writes_candidate_yaml(self, tmp_path: Path) -> None:
        sign_id = write_candidate(
            trigger="bash_deny:pipe-to-shell",
            instruction="Do not run commands matching `pipe-to-shell`",
            reason="blocked by bash deny-list",
            source="bash_deny.sh",
            base_path=str(tmp_path),
        )
        assert sign_id is not None and len(sign_id) == 8
        path = tmp_path / ".crucible" / "inbox" / "signs" / f"{sign_id}.yaml"
        data = yaml.safe_load(path.read_text())
        assert data["trigger"] == "bash_deny:pipe-to-shell"
        assert data["id"] == sign_id
        assert "bash_deny.sh" in data["provenance"]

    def test_dedup_by_trigger(self, tmp_path: Path) -> None:
        a = write_candidate("t", "i", "r", "s", base_path=str(tmp_path))
        b = write_candidate("t", "i2", "r2", "s2", base_path=str(tmp_path))
        assert a is not None
        assert b is None
        signs_dir = tmp_path / ".crucible" / "inbox" / "signs"
        assert len(list(signs_dir.glob("*.yaml"))) == 1

    def test_unwritable_base_fails_silent(self) -> None:
        assert write_candidate("t", "i", "r", "s", base_path="/nonexistent/nope") is None


class TestListCandidates:
    def test_pending_and_acked_split(self, tmp_path: Path) -> None:
        sign_id = write_candidate("t1", "i", "r", "s", base_path=str(tmp_path))
        write_candidate("t2", "i", "r", "s", base_path=str(tmp_path))
        signs_dir = tmp_path / ".crucible" / "inbox" / "signs"
        acked = signs_dir / "acked"
        acked.mkdir()
        (signs_dir / f"{sign_id}.yaml").rename(acked / f"{sign_id}.yaml")

        pending, acked_list = list_candidates(base_path=str(tmp_path))
        assert len(pending) == 1
        assert len(acked_list) == 1
        assert acked_list[0]["id"] == sign_id

    def test_empty_inbox(self, tmp_path: Path) -> None:
        assert list_candidates(base_path=str(tmp_path)) == ([], [])

    def test_malformed_candidate_skipped(self, tmp_path: Path) -> None:
        signs_dir = tmp_path / ".crucible" / "inbox" / "signs"
        signs_dir.mkdir(parents=True)
        (signs_dir / "bad.yaml").write_text("{ not yaml [")
        write_candidate("good", "i", "r", "s", base_path=str(tmp_path))
        pending, _ = list_candidates(base_path=str(tmp_path))
        assert len(pending) == 1
