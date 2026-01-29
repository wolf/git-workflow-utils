"""Tests for git module."""

import subprocess
from pathlib import Path

import pytest

from git_workflow_utils.git import (
    current_branch,
    fetch_all,
    filter_repos_by_ignore_file,
    find_branches,
    find_git_repos,
    get_branch_description,
    get_branch_upstream,
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

class TestFindGitReposWorktrees:
    """Tests for find_git_repos worktree filtering."""

    def test_exclude_worktrees(self, tmp_path):
        """Test that include_worktrees=False excludes worktrees."""
        # Create main repo
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        run_git("init", repo=main_repo)
        (main_repo / "file.txt").write_text("content")
        run_git("add", "file.txt", repo=main_repo)
        run_git("commit", "-m", "Initial commit", repo=main_repo)

        # Create worktree (has .git file, not directory)
        worktree = tmp_path / "worktree"
        run_git("worktree", "add", str(worktree), "HEAD", repo=main_repo)

        # With include_worktrees=True (default), should find both
        all_repos = list(find_git_repos(tmp_path, include_worktrees=True))
        assert len(all_repos) == 2
        assert main_repo in all_repos
        assert worktree in all_repos

        # With include_worktrees=False, should only find main repo
        main_only = list(find_git_repos(tmp_path, include_worktrees=False))
        assert len(main_only) == 1
        assert main_repo in main_only
        assert worktree not in main_only


class TestFilterReposByIgnoreFile:
    """Tests for filter_repos_by_ignore_file function."""

    def test_simple_pattern(self, tmp_path):
        """Test basic ignore file with simple repo name."""
        # Create repos
        repo1 = tmp_path / "active-repo"
        repo2 = tmp_path / "archived-repo"
        repo1.mkdir()
        repo2.mkdir()
        run_git("init", repo=repo1)
        run_git("init", repo=repo2)

        # Create ignore file
        ignore_file = tmp_path / ".testignore"
        ignore_file.write_text("archived-repo\n")

        # Apply filtering
        all_repos = list(find_git_repos(tmp_path))
        filtered = list(filter_repos_by_ignore_file(all_repos, tmp_path, ".testignore"))

        assert repo1 in filtered
        assert repo2 not in filtered

    def test_wildcard_pattern(self, tmp_path):
        """Test ignore file with wildcard patterns."""
        # Create repos
        repos = [
            tmp_path / "active-project",
            tmp_path / "archived-old",
            tmp_path / "archived-2023",
        ]
        for repo in repos:
            repo.mkdir()
            run_git("init", repo=repo)

        # Create ignore file with wildcard
        ignore_file = tmp_path / ".testignore"
        ignore_file.write_text("archived-*\n")

        # Apply filtering
        all_repos = list(find_git_repos(tmp_path))
        filtered = list(filter_repos_by_ignore_file(all_repos, tmp_path, ".testignore"))

        assert repos[0] in filtered  # active-project
        assert repos[1] not in filtered  # archived-old
        assert repos[2] not in filtered  # archived-2023

    def test_negation_pattern(self, tmp_path):
        """Test ignore file with negation patterns."""
        # Create repos in subdirectory
        third_party = tmp_path / "third-party"
        third_party.mkdir()

        repos = [
            third_party / "lib1",
            third_party / "lib2",
            third_party / "important",
        ]
        for repo in repos:
            repo.mkdir()
            run_git("init", repo=repo)

        # Create ignore file: ignore third-party/* except important
        ignore_file = tmp_path / ".testignore"
        ignore_file.write_text("third-party/*\n!third-party/important\n")

        # Apply filtering
        all_repos = list(find_git_repos(tmp_path))
        filtered = list(filter_repos_by_ignore_file(all_repos, tmp_path, ".testignore"))

        assert repos[0] not in filtered  # lib1 ignored
        assert repos[1] not in filtered  # lib2 ignored
        assert repos[2] in filtered  # important un-ignored

    def test_comments(self, tmp_path):
        """Test that comments in ignore files are ignored."""
        # Create repo
        repo = tmp_path / "test-repo"
        repo.mkdir()
        run_git("init", repo=repo)

        # Create ignore file with comments
        ignore_file = tmp_path / ".testignore"
        ignore_file.write_text("# This is a comment\n# test-repo should not be ignored\n")

        # Apply filtering - repo should NOT be filtered
        all_repos = list(find_git_repos(tmp_path))
        filtered = list(filter_repos_by_ignore_file(all_repos, tmp_path, ".testignore"))

        assert repo in filtered


class TestGetBranchDescription:
    """Tests for get_branch_description function."""

    def test_returns_none_when_no_description(self, git_repo):
        desc = get_branch_description("main", git_repo)
        assert desc is None

    def test_returns_description_when_set(self, git_repo):
        subprocess.run(
            ["git", "config", "branch.main.description", "This is the main branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        desc = get_branch_description("main", git_repo)
        assert desc == "This is the main branch"

    def test_returns_multiline_description(self, git_repo):
        subprocess.run(
            ["git", "config", "branch.main.description", "Line 1\nLine 2\nLine 3"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        desc = get_branch_description("main", git_repo)
        assert "Line 1" in desc
        assert "Line 2" in desc

    def test_works_with_current_directory(self, git_repo, monkeypatch):
        subprocess.run(
            ["git", "config", "branch.main.description", "Test description"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        monkeypatch.chdir(git_repo)
        desc = get_branch_description("main")
        assert desc == "Test description"

    def test_returns_none_for_nonexistent_branch(self, git_repo):
        desc = get_branch_description("nonexistent", git_repo)
        assert desc is None


class TestGetBranchUpstream:
    """Tests for get_branch_upstream function."""

    def test_returns_none_when_no_upstream(self, git_repo):
        upstream = get_branch_upstream("main", git_repo)
        assert upstream is None

    def test_returns_upstream_when_set(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        upstream = get_branch_upstream("main", git_repo)
        assert upstream == "origin/main"

    def test_works_with_current_directory(self, git_repo_with_remote, monkeypatch):
        git_repo, _ = git_repo_with_remote
        monkeypatch.chdir(git_repo)
        upstream = get_branch_upstream("main")
        assert upstream == "origin/main"

    def test_returns_none_for_nonexistent_branch(self, git_repo):
        upstream = get_branch_upstream("nonexistent", git_repo)
        assert upstream is None

    def test_returns_upstream_for_feature_branch(self, git_repo_with_remote):
        git_repo, remote = git_repo_with_remote
        # Create and push a feature branch
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        upstream = get_branch_upstream("feature", git_repo)
        assert upstream == "origin/feature"
