"""Pytest wrappers for the hook shell-test suites.

The hook scripts are bash; their tests are bash too (they need a real
shell, real stdin JSON, and to run under /bin/bash to catch bash-3.2
portability bugs). These wrappers make `pytest` run them so the hooks
get CI coverage alongside the Python suite.

Each wrapper invokes the corresponding tests/*.sh under /bin/bash and
asserts a zero exit. The shell script prints which interpreter it used
and a per-failure diagnostic, surfaced via capsys on failure.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

TESTS_DIR = Path(__file__).parent

# macOS ships /bin/bash 3.2; prefer it to exercise the worst-case
# interpreter. Fall back to whatever `bash` is on PATH elsewhere (Linux
# CI typically has bash 5.x as /bin/bash, which is also fine).
_BIN_BASH = "/bin/bash" if Path("/bin/bash").exists() else (shutil.which("bash") or "bash")


def _run_shell_suite(script_name: str) -> subprocess.CompletedProcess:
    script = TESTS_DIR / script_name
    assert script.exists(), f"missing shell test: {script}"
    return subprocess.run(
        [_BIN_BASH, str(script)],
        capture_output=True,
        text=True,
        timeout=120,
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_magic_comments_shell_suite() -> None:
    result = _run_shell_suite("test_magic_comments.sh")
    assert result.returncode == 0, (
        f"magic_comments shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_npm_install_gate_shell_suite() -> None:
    result = _run_shell_suite("test_npm_install_gate.sh")
    assert result.returncode == 0, (
        f"npm_install_gate shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_settings_integrity_shell_suite() -> None:
    result = _run_shell_suite("test_settings_integrity.sh")
    assert result.returncode == 0, (
        f"settings_integrity shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_bash_deny_shell_suite() -> None:
    result = _run_shell_suite("test_bash_deny.sh")
    assert result.returncode == 0, (
        f"bash_deny shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_config_diff_shell_suite() -> None:
    result = _run_shell_suite("test_config_diff.sh")
    assert result.returncode == 0, (
        f"config_diff shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_route_hook_shell_suite() -> None:
    result = _run_shell_suite("test_route_hook.sh")
    assert result.returncode == 0, (
        f"route.sh shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


@pytest.mark.skipif(not Path("/bin/bash").exists() and not shutil.which("bash"), reason="no bash available")
def test_inherit_shell_suite() -> None:
    result = _run_shell_suite("test_inherit.sh")
    assert result.returncode == 0, (
        f"inherit shell suite failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
