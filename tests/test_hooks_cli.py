"""Tests for hooks CLI commands."""

import subprocess
import tempfile
from pathlib import Path

import pytest


def run_cli(*args: str, cwd: str | None = None) -> subprocess.CompletedProcess:
    """Run crucible CLI and return result."""
    return subprocess.run(
        ["python", "-m", "crucible.cli", *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def create_git_repo(path: Path) -> None:
    """Initialize a git repo at path."""
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)


class TestHooksInstall:
    """Test crucible hooks install command."""

    def test_install_fresh_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("hooks", "install", tmpdir)
            assert result.returncode == 0
            assert "Installed pre-commit hook" in result.stdout

            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            assert hook_path.exists()
            content = hook_path.read_text()
            assert "crucible" in content

    def test_install_already_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # First install
            run_cli("hooks", "install", tmpdir)

            # Second install without force
            result = run_cli("hooks", "install", tmpdir)
            assert result.returncode == 0
            assert "already installed" in result.stdout

    def test_install_force_reinstall(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # First install
            run_cli("hooks", "install", tmpdir)

            # Force reinstall
            result = run_cli("hooks", "install", "--force", tmpdir)
            assert result.returncode == 0
            assert "Installed" in result.stdout

    def test_install_existing_non_crucible_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # Create existing hook
            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            hook_path.write_text("#!/bin/sh\necho 'custom hook'")

            result = run_cli("hooks", "install", tmpdir)
            assert result.returncode == 1
            assert "already exists" in result.stdout

    def test_install_force_replaces_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # Create existing hook
            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            hook_path.write_text("#!/bin/sh\necho 'custom hook'")

            result = run_cli("hooks", "install", "--force", tmpdir)
            assert result.returncode == 0

            content = hook_path.read_text()
            assert "crucible" in content

    def test_install_not_a_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_cli("hooks", "install", tmpdir)
            assert result.returncode == 1
            assert "not a git repository" in result.stdout


class TestHooksUninstall:
    """Test crucible hooks uninstall command."""

    def test_uninstall_crucible_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))
            run_cli("hooks", "install", tmpdir)

            result = run_cli("hooks", "uninstall", tmpdir)
            assert result.returncode == 0
            assert "Removed" in result.stdout

            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            assert not hook_path.exists()

    def test_uninstall_no_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("hooks", "uninstall", tmpdir)
            assert result.returncode == 0
            assert "No pre-commit hook installed" in result.stdout

    def test_uninstall_non_crucible_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            hook_path.write_text("#!/bin/sh\necho 'custom'")

            result = run_cli("hooks", "uninstall", tmpdir)
            assert result.returncode == 1
            assert "wasn't installed by crucible" in result.stdout


class TestHooksStatus:
    """Test crucible hooks status command."""

    def test_status_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))
            run_cli("hooks", "install", tmpdir)

            result = run_cli("hooks", "status", tmpdir)
            assert result.returncode == 0
            assert "INSTALLED (crucible)" in result.stdout

    def test_status_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("hooks", "status", tmpdir)
            assert result.returncode == 0
            assert "NOT INSTALLED" in result.stdout

    def test_status_non_crucible_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            hook_path = Path(tmpdir) / ".git" / "hooks" / "pre-commit"
            hook_path.write_text("#!/bin/sh\necho 'custom'")

            result = run_cli("hooks", "status", tmpdir)
            assert result.returncode == 0
            assert "EXISTS (not crucible)" in result.stdout

    def test_status_shows_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # Create config
            config_dir = Path(tmpdir) / ".crucible"
            config_dir.mkdir()
            (config_dir / "precommit.yaml").write_text("fail_on: medium")

            result = run_cli("hooks", "status", tmpdir)
            assert result.returncode == 0
            assert "precommit.yaml" in result.stdout
            assert "(project)" in result.stdout

    def test_status_shows_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("hooks", "status", tmpdir)
            assert "using defaults" in result.stdout


class TestPrecommitCommand:
    """Test crucible pre-commit command."""

    def test_precommit_no_staged_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("pre-commit", tmpdir)
            assert result.returncode == 0
            assert "0 file(s)" in result.stdout

    def test_precommit_with_sensitive_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            # Create and stage a sensitive file
            env_file = Path(tmpdir) / ".env"
            env_file.write_text("SECRET=value")
            subprocess.run(["git", "add", "-f", ".env"], cwd=tmpdir, capture_output=True)

            result = run_cli("pre-commit", tmpdir)
            assert result.returncode == 1
            assert "BLOCKED" in result.stdout
            assert ".env" in result.stdout

    def test_precommit_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("pre-commit", "--json", tmpdir)
            assert result.returncode == 0
            assert '"passed": true' in result.stdout
            assert '"findings": []' in result.stdout

    def test_precommit_fail_on_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("pre-commit", "--fail-on", "critical", tmpdir)
            assert result.returncode == 0

    def test_precommit_verbose(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            create_git_repo(Path(tmpdir))

            result = run_cli("pre-commit", "--verbose", tmpdir)
            assert result.returncode == 0
