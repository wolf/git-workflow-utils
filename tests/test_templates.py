"""Tests for templates module."""

import subprocess
from pathlib import Path

import pytest

from git_workflow_utils.templates import apply_user_template, symlink_envrc_if_needed


class TestSymlinkEnvrcIfNeeded:
    """Tests for symlink_envrc_if_needed function."""

    def test_returns_envrc_when_already_exists(self, git_repo):
        """Should return .envrc if it already exists."""
        envrc = git_repo / ".envrc"
        envrc.write_text("export EXISTING=1")

        result = symlink_envrc_if_needed(git_repo)
        assert result == envrc
        assert envrc.is_file()
        assert not envrc.is_symlink()

    def test_creates_symlink_from_sample(self, git_repo):
        """Should create symlink from .envrc.sample if .envrc doesn't exist."""
        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export SAMPLE=1")

        result = symlink_envrc_if_needed(git_repo)
        envrc = git_repo / ".envrc"

        assert result == envrc
        assert envrc.is_symlink()
        assert envrc.readlink() == Path(".envrc.sample")
        assert envrc.read_text() == "export SAMPLE=1"

    def test_returns_none_when_no_template(self, git_repo):
        """Should return None if neither .envrc nor .envrc.sample exists."""
        result = symlink_envrc_if_needed(git_repo)
        assert result is None

    def test_custom_template_name(self, git_repo):
        """Should support custom template filename."""
        template = git_repo / ".envrc.template"
        template.write_text("export TEMPLATE=1")

        result = symlink_envrc_if_needed(git_repo, template=".envrc.template")
        envrc = git_repo / ".envrc"

        assert result == envrc
        assert envrc.is_symlink()
        assert envrc.readlink() == Path(".envrc.template")

    def test_doesnt_overwrite_existing_envrc(self, git_repo):
        """Should not overwrite .envrc if it already exists."""
        envrc = git_repo / ".envrc"
        envrc.write_text("export EXISTING=1")

        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export SAMPLE=1")

        result = symlink_envrc_if_needed(git_repo)

        assert result == envrc
        assert not envrc.is_symlink()
        assert envrc.read_text() == "export EXISTING=1"


class TestApplyUserTemplate:
    """Tests for apply_user_template function."""

    def test_does_nothing_when_no_template_exists(self, git_repo):
        """Should silently return if no template directory exists."""
        # Should not raise
        apply_user_template(git_repo)

    def test_raises_when_template_exists_but_no_mode_configured(self, git_repo, tmp_path):
        """Should raise RuntimeError if template exists but mode not configured."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")

        with pytest.raises(RuntimeError, match="worktree.userTemplate.mode is not configured"):
            apply_user_template(git_repo, template_path=template_dir)

    def test_raises_on_invalid_mode(self, git_repo, tmp_path):
        """Should raise RuntimeError if mode is invalid."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")

        # Set invalid mode
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "invalid"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        with pytest.raises(RuntimeError, match="Invalid worktree.userTemplate.mode"):
            apply_user_template(git_repo, template_path=template_dir)

    def test_symlinks_files_in_link_mode(self, git_repo, tmp_path):
        """Should create symlinks when mode is 'link'."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")
        (template_dir / ".custom").write_text("custom content")

        # Configure link mode
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "link"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        envrc_local = git_repo / ".envrc.local"
        custom = git_repo / ".custom"

        assert envrc_local.is_symlink()
        assert envrc_local.resolve() == (template_dir / ".envrc.local").resolve()
        assert custom.is_symlink()
        assert custom.resolve() == (template_dir / ".custom").resolve()

    def test_copies_files_in_copy_mode(self, git_repo, tmp_path):
        """Should copy files when mode is 'copy'."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")

        # Configure copy mode
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "copy"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        envrc_local = git_repo / ".envrc.local"

        assert envrc_local.is_file()
        assert not envrc_local.is_symlink()
        assert envrc_local.read_text() == "export LOCAL=1"

    def test_copies_directories_in_copy_mode(self, git_repo, tmp_path):
        """Should recursively copy directories when mode is 'copy'."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        ipython_dir = template_dir / ".ipython"
        ipython_dir.mkdir()
        (ipython_dir / "config.py").write_text("# config")
        (ipython_dir / "startup").mkdir()
        (ipython_dir / "startup" / "00-imports.py").write_text("import os")

        # Configure copy mode
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "copy"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        ipython = git_repo / ".ipython"

        assert ipython.is_dir()
        assert not ipython.is_symlink()
        assert (ipython / "config.py").read_text() == "# config"
        assert (ipython / "startup" / "00-imports.py").read_text() == "import os"

    def test_per_file_override_link_in_copy_mode(self, git_repo, tmp_path):
        """Should respect per-file overrides (link specific file in copy mode)."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")
        (template_dir / ".custom").write_text("custom")

        # Configure copy mode but override .envrc.local to link
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "copy"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--add", "worktree.userTemplate.link", ".envrc.local"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        envrc_local = git_repo / ".envrc.local"
        custom = git_repo / ".custom"

        assert envrc_local.is_symlink()  # Overridden to link
        assert not custom.is_symlink()   # Default copy

    def test_per_file_override_copy_in_link_mode(self, git_repo, tmp_path):
        """Should respect per-file overrides (copy specific file in link mode)."""
        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")
        (template_dir / ".custom").write_text("custom")

        # Configure link mode but override .custom to copy
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "link"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "--add", "worktree.userTemplate.copy", ".custom"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        envrc_local = git_repo / ".envrc.local"
        custom = git_repo / ".custom"

        assert envrc_local.is_symlink()  # Default link
        assert not custom.is_symlink()   # Overridden to copy

    def test_skips_existing_files(self, git_repo, tmp_path):
        """Should not overwrite files that already exist."""
        # Create existing file
        existing = git_repo / ".envrc.local"
        existing.write_text("export EXISTING=1")

        template_dir = tmp_path / "template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export TEMPLATE=1")
        (template_dir / ".custom").write_text("custom")

        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "link"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo, template_path=template_dir)

        # Existing file should not be touched
        assert existing.read_text() == "export EXISTING=1"
        assert not existing.is_symlink()

        # New file should be created
        custom = git_repo / ".custom"
        assert custom.is_symlink()

    def test_uses_default_template_location(self, git_repo, tmp_path, monkeypatch):
        """Should use ~/.config/git/user-template/ as default location."""
        # Create default template location
        default_template = tmp_path / ".config" / "git" / "user-template"
        default_template.mkdir(parents=True)
        (default_template / ".envrc.local").write_text("export LOCAL=1")

        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "link"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo)

        envrc_local = git_repo / ".envrc.local"
        assert envrc_local.is_symlink()

    def test_uses_git_config_path(self, git_repo, tmp_path):
        """Should use path from git config worktree.userTemplate.path."""
        template_dir = tmp_path / "my-custom-template"
        template_dir.mkdir()
        (template_dir / ".envrc.local").write_text("export LOCAL=1")

        # Configure custom path and mode
        subprocess.run(
            ["git", "config", "worktree.userTemplate.path", str(template_dir)],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "worktree.userTemplate.mode", "link"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        apply_user_template(git_repo)

        envrc_local = git_repo / ".envrc.local"
        assert envrc_local.is_symlink()
