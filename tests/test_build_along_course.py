"""Tests for the bundled meta/build-along-course skill.

Covers three things per the spec's acceptance criteria:
  1. Content assertions on SKILL.md (provenance, vault cascade order,
     never-regenerate rule, zero-external-requests rule).
  2. styles.css and base.html make zero external requests (no
     http://, no https://).
  3. assemble.sh's assembly/failure behavior, exercised as a real
     subprocess under /bin/bash (bash-3.2-safe — no mapfile, no
     globstar, no associative arrays).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import crucible

SKILL_DIR = Path(crucible.__file__).parent / "skills" / "meta" / "build-along-course"
REFERENCES = SKILL_DIR / "references"


class TestSkillContent:
    """Content assertions on SKILL.md itself."""

    def _text(self) -> str:
        return (SKILL_DIR / "SKILL.md").read_text()

    def test_provenance_line_present(self) -> None:
        text = self._text()
        assert "Original to crucible" in text
        assert "Zara Zhang" in text
        assert "codebase-to-course" in text
        assert "no code or text reused" in text

    def test_vault_cascade_order_documented(self) -> None:
        text = self._text()
        project_idx = text.index(".crucible/teach.yaml")
        user_idx = text.index("~/.claude/crucible/teach.yaml")
        assert project_idx < user_idx, (
            ".crucible/teach.yaml must be documented before "
            "~/.claude/crucible/teach.yaml (project-then-user cascade order)"
        )

    def test_never_regenerate_rule_present(self) -> None:
        text = self._text().lower()
        assert "never regenerate" in text

    def test_zero_external_requests_documented(self) -> None:
        text = self._text().lower()
        assert "zero external requests" in text or "no external requests" in text

    def test_module_zero_is_spec(self) -> None:
        text = self._text()
        assert "module 0" in text.lower() or '`00`' in text

    def test_do_not_boundary_present(self) -> None:
        text = self._text()
        assert "Do NOT" in text

    def test_all_seven_reference_files_exist(self) -> None:
        expected = [
            "styles.css",
            "course.js",
            "base.html",
            "footer.html",
            "module-template.html",
            "assemble.sh",
            "content-guide.md",
        ]
        missing = [f for f in expected if not (REFERENCES / f).exists()]
        assert missing == [], f"missing reference files: {missing}"


class TestZeroExternalRequests:
    """styles.css and base.html must never point off-disk."""

    def test_styles_css_has_no_urls(self) -> None:
        text = (REFERENCES / "styles.css").read_text()
        assert "http://" not in text
        assert "https://" not in text

    def test_base_html_has_no_urls(self) -> None:
        text = (REFERENCES / "base.html").read_text()
        assert "http://" not in text
        assert "https://" not in text


class TestAssembleSh:
    """Exercise assemble.sh as a real subprocess under /bin/bash."""

    def _make_course(self, tmp_path: Path) -> Path:
        course = tmp_path / "course"
        (course / "modules").mkdir(parents=True)
        (course / "base.html").write_text("BASE_CONTENT\n")
        (course / "footer.html").write_text("FOOTER_CONTENT\n")
        (course / "modules" / "01-a.html").write_text("MODULE_01_A\n")
        (course / "modules" / "02-b.html").write_text("MODULE_02_B\n")
        return course

    def _run(self, course: Path) -> subprocess.CompletedProcess[str]:
        script = REFERENCES / "assemble.sh"
        return subprocess.run(
            ["/bin/bash", str(script), str(course)],
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_assembles_in_order_base_first_footer_last(self, tmp_path: Path) -> None:
        course = self._make_course(tmp_path)
        result = self._run(course)
        assert result.returncode == 0, result.stderr

        index = (course / "index.html").read_text()
        assert "MODULE_01_A" in index
        assert "MODULE_02_B" in index

        base_idx = index.index("BASE_CONTENT")
        mod1_idx = index.index("MODULE_01_A")
        mod2_idx = index.index("MODULE_02_B")
        footer_idx = index.index("FOOTER_CONTENT")
        assert base_idx < mod1_idx < mod2_idx < footer_idx, (
            "expected order: base, module 01, module 02, footer"
        )

    def test_missing_footer_fails_nonzero(self, tmp_path: Path) -> None:
        course = self._make_course(tmp_path)
        (course / "footer.html").unlink()
        result = self._run(course)
        assert result.returncode != 0
        assert result.stderr.strip() != ""

    def test_missing_base_fails_nonzero(self, tmp_path: Path) -> None:
        course = self._make_course(tmp_path)
        (course / "base.html").unlink()
        result = self._run(course)
        assert result.returncode != 0
        assert result.stderr.strip() != ""

    def test_empty_modules_dir_fails_nonzero(self, tmp_path: Path) -> None:
        course = self._make_course(tmp_path)
        for f in (course / "modules").glob("*.html"):
            f.unlink()
        result = self._run(course)
        assert result.returncode != 0
        assert result.stderr.strip() != ""

    def test_never_edits_module_files(self, tmp_path: Path) -> None:
        course = self._make_course(tmp_path)
        mod1 = course / "modules" / "01-a.html"
        mod2 = course / "modules" / "02-b.html"
        before = {mod1: mod1.read_text(), mod2: mod2.read_text()}

        result = self._run(course)
        assert result.returncode == 0, result.stderr

        assert mod1.read_text() == before[mod1]
        assert mod2.read_text() == before[mod2]
