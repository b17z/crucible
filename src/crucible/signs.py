"""Candidate Sign store for the GUARDRAILS auto-append machinery.

Deny events write candidates here; `crucible-sign:` acknowledges them;
the Stop hook appends acknowledged Signs to GUARDRAILS.md. Everything in
this module fails silent — a Sign is a nice-to-have record, and its
bookkeeping must never break the deny path that produced it.
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

import yaml

SIGNS_INBOX = Path(".crucible") / "inbox" / "signs"


def write_candidate(
    trigger: str,
    instruction: str,
    reason: str,
    source: str,
    base_path: str = ".",
) -> str | None:
    """Write a candidate Sign; returns its id, or None on dedup/failure."""
    try:
        sign_id = hashlib.sha256(trigger.encode()).hexdigest()[:8]
        inbox = Path(base_path) / SIGNS_INBOX
        inbox.mkdir(parents=True, exist_ok=True)
        path = inbox / f"{sign_id}.yaml"
        if path.exists() or (inbox / "acked" / f"{sign_id}.yaml").exists():
            return None  # dedup: same trigger already pending or acked
        payload = {
            "id": sign_id,
            "trigger": trigger,
            "instruction": instruction,
            "reason": reason,
            "provenance": f"{date.today().isoformat()} via {source}",
        }
        path.write_text(yaml.safe_dump(payload, sort_keys=False))
        return sign_id
    except Exception:  # crucible-ignore: no-catch-exception -- fail-silent boundary: Sign bookkeeping must never break a deny path
        return None


def _load_dir(directory: Path) -> list[dict]:
    if not directory.exists():
        return []
    out: list[dict] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text())
        except (yaml.YAMLError, OSError):
            continue
        if isinstance(data, dict) and data.get("id"):
            out.append(data)
    return out


def list_candidates(base_path: str = ".") -> tuple[list[dict], list[dict]]:
    """(pending, acked) candidate Signs."""
    inbox = Path(base_path) / SIGNS_INBOX
    return _load_dir(inbox), _load_dir(inbox / "acked")
