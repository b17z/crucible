"""File-integrity baselines for the v2 publisher-security defense.

Watched files (``.claude/settings.json``, ``.mcp.json``,
``.vscode/extensions.json``) get hashed once at ``crucible baselines init``.
Hashes live in ``.crucible/baselines/<name>.sha256``, outside any path
TeamPCP can modify by editing the watched files themselves.

A ``manifest.sha256`` covers all individual baselines so that an attacker
who modifies one watched file AND its baseline still gets caught — the
manifest hash diverges.

See ``src/crucible/skills_core/SPEC.md`` and the v2 handoff Part 5 for
the threat model and the FileChanged hook flow that consumes these.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from crucible.errors import Result, err, ok

BASELINES_DIR = Path(".crucible") / "baselines"

# Each watched file maps to a baseline filename (sans extension).
# Order matters: it determines manifest hash input order.
WATCHED_FILES: tuple[tuple[str, Path], ...] = (
    ("settings", Path(".claude") / "settings.json"),
    ("mcp", Path(".mcp.json")),
    ("extensions", Path(".vscode") / "extensions.json"),
)

MANIFEST_NAME = "manifest"


@dataclass(frozen=True)
class BaselineEntry:
    """One watched file's baseline state at init time."""

    name: str  # e.g., "settings"
    watched_path: Path
    baseline_path: Path  # .crucible/baselines/<name>.sha256
    file_existed: bool  # False if the watched file was absent at init time
    sha256: str | None  # None if file_existed is False


def hash_file(path: Path) -> str:
    """SHA-256 of a file's contents, lowercase hex."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_manifest(entries: list[BaselineEntry]) -> str:
    """Hash that covers every individual baseline + the absence of others.

    Anti-tamper anchor: if an attacker modifies a single ``<name>.sha256``
    to match an injected change, this manifest's input has shifted and the
    saved manifest no longer matches.

    Format of hashed input: one line per entry, ``<name> <sha256-or-MISSING>\\n``,
    in WATCHED_FILES order.
    """
    h = hashlib.sha256()
    for entry in entries:
        value = entry.sha256 if entry.sha256 is not None else "MISSING"
        h.update(f"{entry.name} {value}\n".encode())
    return h.hexdigest()


def init_baselines(force: bool = False) -> Result[list[BaselineEntry], str]:
    """Capture baselines for every watched file in the current project.

    Refuses to overwrite an existing baseline directory unless ``force`` is
    True — re-baselining after a compromise would lock in the attacker's
    state. The right recovery path is: investigate, restore the file from
    a known-good source, then re-init with ``--force``.

    Files that don't exist (e.g., a project without ``.vscode/``) are
    recorded as MISSING in the manifest; this means later creation of
    the file will diverge the manifest and trip the FileChanged hook.
    """
    if BASELINES_DIR.exists() and not force:
        return err(
            f"{BASELINES_DIR} already exists. Re-baselining can lock in a "
            "compromised state — investigate, restore, then re-run with --force."
        )

    BASELINES_DIR.mkdir(parents=True, exist_ok=True)

    entries: list[BaselineEntry] = []
    for name, watched in WATCHED_FILES:
        baseline_path = BASELINES_DIR / f"{name}.sha256"
        # Content snapshot alongside the hash so the FileChanged config_diff
        # hook can show WHAT changed, not just that something did. Advisory
        # only — the block decision rests on the manifest-covered hashes, so
        # a tampered snapshot can mislabel a diff but never unblock.
        snapshot_path = BASELINES_DIR / f"{name}.snapshot"
        if watched.exists():
            sha = hash_file(watched)
            baseline_path.write_text(f"{sha}\n")
            snapshot_path.write_bytes(watched.read_bytes())
            entries.append(
                BaselineEntry(
                    name=name,
                    watched_path=watched,
                    baseline_path=baseline_path,
                    file_existed=True,
                    sha256=sha,
                )
            )
        else:
            baseline_path.write_text("MISSING\n")
            # A stale snapshot from a prior init would misreport the diff.
            snapshot_path.unlink(missing_ok=True)
            entries.append(
                BaselineEntry(
                    name=name,
                    watched_path=watched,
                    baseline_path=baseline_path,
                    file_existed=False,
                    sha256=None,
                )
            )

    manifest = compute_manifest(entries)
    (BASELINES_DIR / f"{MANIFEST_NAME}.sha256").write_text(f"{manifest}\n")

    return ok(entries)
