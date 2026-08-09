"""Pin the bundled files the wheel must ship (regression guard for
package-data): a file listed here that exists in the repo but not in the
installed package means pyproject's package-data globs regressed."""

from pathlib import Path

import crucible

PKG = Path(crucible.__file__).parent

BUNDLED = [
    "templates/REVIEW.md",
    "templates/GUARDRAILS.md",
    "templates/AGENTS.md",
    "verify/bundled/verifiers.yaml",
    "interfaces/claude_code/stop/append_signs.sh",
    "interfaces/claude_code/stop/review_nudge.sh",
    "interfaces/claude_code/pre_tool_use/bash_deny.sh",
    "policies/dependency_quarantine.yaml",
    "policies/settings_integrity.yaml",
    "policies/bash_denylist.yaml",
    "skills/meta/brainstorming/SKILL.md",
    "skills/meta/systematic-debugging/SKILL.md",
    "skills/meta/tdd/SKILL.md",
    "skills/meta/wait-what/SKILL.md",
    "skills/meta/teach-me/SKILL.md",
    "skills/meta/engineering-loop/SKILL.md",
    "skills/meta/build-along-course/SKILL.md",
    "skills/meta/build-along-course/references/styles.css",
    "skills/meta/build-along-course/references/course.js",
    "skills/meta/build-along-course/references/base.html",
    "skills/meta/build-along-course/references/footer.html",
    "skills/meta/build-along-course/references/module-template.html",
    "skills/meta/build-along-course/references/assemble.sh",
    "skills/meta/build-along-course/references/content-guide.md",
]


def test_bundled_files_ship() -> None:
    missing = [rel for rel in BUNDLED if not (PKG / rel).exists()]
    assert missing == [], f"bundled files missing from installed package: {missing}"
