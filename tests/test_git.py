"""Tests for git module."""

import subprocess
from pathlib import Path

import pytest

from git_workflow_utils.git import (
    current_branch,
    fetch_all,
    find_branches,
    find_git_repos,
    get_commits,
    has_uncommitted_changes,
    initialize_repo,
    run_git,
    submodule_update,
    user_email_in_this_working_copy,
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


class TestFindGitRepos:
    """Tests for find_git_repos function."""

    def test_finds_single_repo(self, tmp_path, git_repo):
        repos = list(find_git_repos(tmp_path))
        assert git_repo in repos

    def test_finds_multiple_repos(self, tmp_path):
        # Create multiple repos
        repo1 = tmp_path / "repo1"
        repo1.mkdir()
        subprocess.run(["git", "init"], cwd=repo1, check=True, capture_output=True)

        repo2 = tmp_path / "repo2"
        repo2.mkdir()
        subprocess.run(["git", "init"], cwd=repo2, check=True, capture_output=True)

        repos = list(find_git_repos(tmp_path))
        assert repo1 in repos
        assert repo2 in repos

    def test_finds_nested_repos(self, tmp_path):
        # Create nested structure
        parent = tmp_path / "parent"
        parent.mkdir()
        subprocess.run(["git", "init"], cwd=parent, check=True, capture_output=True)

        child = parent / "child"
        child.mkdir()
        subprocess.run(["git", "init"], cwd=child, check=True, capture_output=True)

        repos = list(find_git_repos(tmp_path))
        assert parent in repos
        assert child in repos

    def test_handles_worktrees(self, tmp_path, git_repo):
        # Create a worktree
        worktree_path = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        repos = list(find_git_repos(tmp_path))
        assert git_repo in repos
        assert worktree_path in repos


class TestUserEmailInThisWorkingCopy:
    """Tests for user_email_in_this_working_copy function."""

    def test_returns_configured_email(self, git_repo):
        email = user_email_in_this_working_copy(git_repo)
        assert email == "test@example.com"

    def test_returns_global_email_when_local_not_configured(self, tmp_path):
        # Create repo without local email config (will fall back to global)
        repo = tmp_path / "no-local-email-repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)

        email = user_email_in_this_working_copy(repo)
        # Should return global config if local not set
        assert email is not None

    def test_works_with_current_directory(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        email = user_email_in_this_working_copy()
        assert email == "test@example.com"


class TestGetCommits:
    """Tests for get_commits function."""

    def test_returns_commits_by_author(self, git_repo):
        commits = list(get_commits(repo=git_repo, author_email="test@example.com"))
        assert len(commits) == 1
        assert commits[0][1] == "Initial commit"

    def test_returns_empty_for_different_author(self, git_repo):
        commits = list(get_commits(repo=git_repo, author_email="other@example.com"))
        assert len(commits) == 0

    def test_filters_by_since(self, git_repo):
        # Get initial commit time for reference
        import time
        time.sleep(2)  # Wait to ensure time difference

        # Create new commit
        (git_repo / "new.txt").write_text("new")
        subprocess.run(["git", "add", "new.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "New commit"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        # Get commits since 1 second ago (should only get the new one)
        commits = list(get_commits(repo=git_repo, since="1 second ago", author_email="test@example.com"))
        assert len(commits) == 1
        assert commits[0][1] == "New commit"

    def test_returns_hash_and_summary(self, git_repo):
        commits = list(get_commits(repo=git_repo))
        assert len(commits) == 1
        hash_part, summary = commits[0]
        assert len(hash_part) == 40  # Full SHA
        assert summary == "Initial commit"

    def test_works_without_filters(self, git_repo):
        commits = list(get_commits(repo=git_repo))
        assert len(commits) >= 1
