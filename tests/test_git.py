"""Tests for git module."""

import subprocess
from pathlib import Path

import pytest

from git_workflow_utils.git import (
    current_branch,
    fetch_all,
    find_branches,
    has_uncommitted_changes,
    initialize_repo,
    run_git,
    submodule_update,
)


class TestRunGit:
    """Tests for run_git function."""

    def test_runs_git_command(self, git_repo):
        result = run_git("status", repo=git_repo, capture=True)
        assert result.returncode == 0
        assert "On branch" in result.stdout

    def test_runs_in_current_directory(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        result = run_git("status", capture=True)
        assert result.returncode == 0

    def test_check_false_doesnt_raise(self, git_repo):
        result = run_git("invalid-command", repo=git_repo, check=False, capture=True)
        assert result.returncode != 0

    def test_check_true_raises(self, git_repo):
        with pytest.raises(subprocess.CalledProcessError):
            run_git("invalid-command", repo=git_repo, check=True, capture=True)

    def test_capture_returns_output(self, git_repo):
        result = run_git("branch", "--show-current", repo=git_repo, capture=True)
        assert result.stdout == "main\n"


class TestCurrentBranch:
    """Tests for current_branch function."""

    def test_returns_current_branch(self, git_repo):
        branch = current_branch(git_repo)
        assert branch == "main"

    def test_returns_branch_in_cwd(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        branch = current_branch()
        assert branch == "main"

    def test_returns_different_branch(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        branch = current_branch(git_repo)
        assert branch == "feature"


class TestHasUncommittedChanges:
    """Tests for has_uncommitted_changes function."""

    def test_clean_repo_returns_false(self, git_repo):
        assert has_uncommitted_changes(git_repo) is False

    def test_modified_file_returns_true(self, git_repo):
        (git_repo / "README.md").write_text("# Modified\n")
        assert has_uncommitted_changes(git_repo) is True

    def test_new_file_returns_true(self, git_repo):
        (git_repo / "new.txt").write_text("new content")
        assert has_uncommitted_changes(git_repo) is True

    def test_staged_file_returns_true(self, git_repo):
        new_file = git_repo / "staged.txt"
        new_file.write_text("staged")
        subprocess.run(["git", "add", "staged.txt"], cwd=git_repo, check=True, capture_output=True)
        assert has_uncommitted_changes(git_repo) is True


class TestFetchAll:
    """Tests for fetch_all function."""

    def test_fetches_without_error(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        fetch_all(git_repo)  # Should not raise

    def test_quiet_suppresses_output(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        fetch_all(git_repo, quiet=True)  # Should not raise


class TestFindBranches:
    """Tests for find_branches function."""

    def test_finds_local_branch(self, git_repo):
        branches = find_branches("main", git_repo)
        assert "main" in branches

    def test_finds_remote_branch(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        branches = find_branches("main", git_repo)
        assert "origin/main" in branches

    def test_exact_name_searches_local_and_remote(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        branches = find_branches("main", git_repo)
        # Should find both local and remote
        assert "main" in branches
        assert "origin/main" in branches

    def test_wildcard_pattern(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature-1"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "-b", "feature-2"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        branches = find_branches("feature-*", git_repo)
        assert "feature-1" in branches
        assert "feature-2" in branches

    def test_no_duplicates(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        branches = find_branches("main", git_repo)
        # Should not have duplicates
        assert branches.count("main") == 1

    def test_nonexistent_branch_returns_empty(self, git_repo):
        branches = find_branches("nonexistent", git_repo)
        assert branches == []


class TestSubmoduleUpdate:
    """Tests for submodule_update function."""

    def test_runs_without_error_on_repo_without_submodules(self, git_repo):
        submodule_update(git_repo)  # Should not raise

    def test_runs_in_cwd(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        submodule_update()  # Should not raise


class TestInitializeRepo:
    """Tests for initialize_repo function."""

    def test_initializes_repo_without_error(self, git_repo):
        initialize_repo(git_repo)  # Should not raise

    def test_creates_envrc_symlink_if_sample_exists(self, git_repo, monkeypatch, tmp_path):
        # Create .envrc.sample
        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export TEST=1")

        # Mock direnv to avoid actually running it
        mock_direnv = tmp_path / "direnv"
        mock_direnv.write_text("#!/bin/sh\nexit 0")
        mock_direnv.chmod(0o755)
        import os
        monkeypatch.setenv("PATH", f"{tmp_path}:{os.getenv('PATH', '')}")

        initialize_repo(git_repo)

        envrc = git_repo / ".envrc"
        assert envrc.exists()
        assert envrc.is_symlink()
