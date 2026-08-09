#!/bin/bash
# append_signs.sh — Stop hook for Crucible v2 (Phase 7)
#
# Consumes acknowledged candidate Signs (Task 6 layout:
# .crucible/inbox/signs/acked/*.yaml) and appends them to the project's
# GUARDRAILS.md under the documented Sign format. Signs are numbered
# continuing from the highest existing "### Sign N" heading; the
# template's placeholder line is removed on first append. Acked files
# are deleted once successfully appended.
#
# ADVISORY / BEST-EFFORT — always exits 0. A malformed candidate is
# noted on stderr and left in place for manual inspection; every other
# candidate still gets appended.
#
# Installation: registered by `crucible hooks claudecode init` under
# Stop with no matcher.

set -uo pipefail

ACKED_DIR=".crucible/inbox/signs/acked"

# Nothing acknowledged → silent.
[[ -d "$ACKED_DIR" ]] || exit 0

# Best-effort hook: no python3 means no append, and that's okay.
command -v python3 >/dev/null 2>&1 || exit 0

# Template lives relative to THIS script, not cwd, so it resolves
# correctly regardless of the project the hook runs in.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATE="$SCRIPT_DIR/../../../templates/GUARDRAILS.md"

python3 - "$ACKED_DIR" "$TEMPLATE" << 'PY'
import re
import sys
import tempfile
from pathlib import Path

import yaml

acked_dir = Path(sys.argv[1])
template_path = Path(sys.argv[2])

PLACEHOLDER = "_(none yet — Crucible appends here on user `crucible-sign:` acknowledgement)_"
SIGN_HEADING_RE = re.compile(r"^### Sign (\d+)", re.MULTILINE)
SIGNS_HEADING_RE = re.compile(r"^## Signs\s*$", re.MULTILINE)
NEXT_H2_RE = re.compile(r"^## ", re.MULTILINE)


def load_candidate(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text())
    except (yaml.YAMLError, OSError) as exc:
        print(f"crucible: skipping malformed Sign candidate {path.name}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict) or not data.get("trigger"):
        print(f"crucible: skipping malformed Sign candidate {path.name}: missing 'trigger'", file=sys.stderr)
        return None
    return data


def sign_title(data: dict) -> str:
    instruction = (data.get("instruction") or "").strip()
    if instruction:
        return " ".join(instruction.split()[:6])
    return (data.get("trigger") or "").strip()


def render_sign(number: int, data: dict) -> str:
    title = sign_title(data)
    trigger = data.get("trigger", "")
    instruction = data.get("instruction", "")
    reason = data.get("reason", "")
    provenance = data.get("provenance", "")
    return (
        f"### Sign {number} — {title}\n\n"
        f"- **Trigger:** {trigger}\n"
        f"- **Instruction:** {instruction}\n"
        f"- **Reason:** {reason}\n"
        f"- **Provenance:** {provenance}\n"
    )


paths = sorted(acked_dir.glob("*.yaml"))
if not paths:
    sys.exit(0)

candidates: list[tuple[Path, dict]] = []
for path in paths:
    data = load_candidate(path)
    if data is not None:
        candidates.append((path, data))

if not candidates:
    sys.exit(0)

guardrails_path = Path("GUARDRAILS.md")
if guardrails_path.exists():
    content = guardrails_path.read_text()
elif template_path.exists():
    content = template_path.read_text()
else:
    # No project file and no template to seed from — nothing sane to do.
    sys.exit(0)

existing_numbers = [int(n) for n in SIGN_HEADING_RE.findall(content)]
next_number = max(existing_numbers, default=0) + 1

blocks = []
for _path, data in candidates:
    blocks.append(render_sign(next_number, data))
    next_number += 1

if PLACEHOLDER in content:
    content = content.replace(PLACEHOLDER, "").rstrip("\n") + "\n"

appended = "\n" + "\n".join(blocks)

# Insert at the end of the "## Signs" section: immediately before the
# next "## " heading after it, if one exists. Otherwise append at EOF.
insertion_point = None
signs_match = SIGNS_HEADING_RE.search(content)
if signs_match:
    next_heading_match = NEXT_H2_RE.search(content, signs_match.end())
    if next_heading_match:
        insertion_point = next_heading_match.start()

if insertion_point is not None:
    before = content[:insertion_point].rstrip("\n") + "\n"
    after = content[insertion_point:]
    content = before + appended.rstrip("\n") + "\n\n" + after
else:
    content = content.rstrip("\n") + "\n" + appended

if not content.endswith("\n"):
    content += "\n"

tmp_fd = tempfile.NamedTemporaryFile(
    mode="w",
    dir=guardrails_path.resolve().parent,
    prefix=guardrails_path.name + ".",
    suffix=".tmp",
    delete=False,
)
try:
    tmp_fd.write(content)
    tmp_fd.close()
    Path(tmp_fd.name).replace(guardrails_path)
except BaseException:
    Path(tmp_fd.name).unlink(missing_ok=True)
    raise

for path, _data in candidates:
    try:
        path.unlink()
    except OSError as exc:
        print(f"crucible: appended {path.name} but could not remove it: {exc}", file=sys.stderr)

sys.exit(0)
PY
exit 0
