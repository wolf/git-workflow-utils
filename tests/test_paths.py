"""Tests for paths module."""

from pathlib import Path

import pytest

from git_workflow_utils.paths import (
    is_absolute_repo_path,
    resolve_path,
    resolve_repo,
    sanitize_directory_name,
)


class TestResolvePath:
    """Tests for resolve_path function."""

    def test_none_returns_cwd(self):
        result = resolve_path(None)
        assert result == Path.cwd()

    def test_empty_string_returns_cwd(self):
        result = resolve_path("")
        assert result == Path.cwd()

    def test_expands_tilde(self):
        result = resolve_path("~/test")
        assert "~" not in str(result)
        assert result.is_absolute()

    def test_resolves_relative_path(self):
        result = resolve_path("./test")
        assert result.is_absolute()

    def test_absolute_path_unchanged(self):
        abs_path = Path("/tmp/test")
        result = resolve_path(abs_path)
        assert result == abs_path.resolve()


class TestIsAbsoluteRepoPath:
    """Tests for is_absolute_repo_path function."""

    def test_valid_repo_returns_true(self, git_repo):
        assert is_absolute_repo_path(git_repo) is True

    def test_relative_path_returns_false(self, git_repo):
        # Get a relative path
        relative = Path(git_repo.name)
        assert is_absolute_repo_path(relative) is False

    def test_non_repo_directory_returns_false(self, tmp_path):
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        assert is_absolute_repo_path(non_repo) is False

    def test_file_returns_false(self, tmp_path):
        file_path = tmp_path / "test.txt"
        file_path.write_text("test")
        assert is_absolute_repo_path(file_path) is False

    def test_nonexistent_path_returns_false(self, tmp_path):
        nonexistent = tmp_path / "does-not-exist"
        assert is_absolute_repo_path(nonexistent) is False


class TestResolveRepo:
    """Tests for resolve_repo function."""

    def test_resolves_git_repo(self, git_repo):
        result = resolve_repo(git_repo)
        assert result == git_repo

    def test_current_directory_when_in_repo(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        result = resolve_repo()
        assert result == git_repo

    def test_raises_on_non_repo(self, tmp_path):
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        with pytest.raises(AssertionError):
            resolve_repo(non_repo)

    def test_expands_tilde_in_repo_path(self, git_repo, monkeypatch):
        # This is a bit tricky to test - we'd need to create a repo in home dir
        # For now, just verify it attempts to resolve
        with pytest.raises(AssertionError):
            resolve_repo("~/nonexistent-repo")


class TestSanitizeDirectoryName:
    """Tests for sanitize_directory_name function."""

    def test_replaces_slashes_with_hyphens(self):
        assert sanitize_directory_name("feature/foo") == "feature-foo"
        assert sanitize_directory_name("bugfix/issue-123") == "bugfix-issue-123"

    def test_replaces_all_unsafe_characters(self):
        assert sanitize_directory_name("branch/name") == "branch-name"
        assert sanitize_directory_name("branch\\name") == "branch-name"
        assert sanitize_directory_name("branch:name") == "branch-name"
        assert sanitize_directory_name("branch*name") == "branch-name"
        assert sanitize_directory_name('branch"name') == "branch-name"

    def test_collapses_consecutive_unsafe_chars(self):
        assert sanitize_directory_name("feature//foo") == "feature-foo"
        assert sanitize_directory_name("bug///fix") == "bug-fix"
        assert sanitize_directory_name("test/:/mixed") == "test-mixed"

    def test_strips_leading_and_trailing_hyphens(self):
        assert sanitize_directory_name("/leading") == "leading"
        assert sanitize_directory_name("trailing/") == "trailing"
        assert sanitize_directory_name("/both/") == "both"

    def test_preserves_safe_characters(self):
        assert sanitize_directory_name("feature-123") == "feature-123"
        assert sanitize_directory_name("bug_fix") == "bug_fix"
        assert sanitize_directory_name("test.branch") == "test.branch"

    def test_real_world_examples(self):
        assert sanitize_directory_name("feature/user-auth") == "feature-user-auth"
        assert sanitize_directory_name("bugfix/issue-42/quick-fix") == "bugfix-issue-42-quick-fix"

    def test_raises_on_empty_or_all_unsafe(self):
        with pytest.raises(ValueError, match="empty or contains only unsafe"):
            sanitize_directory_name("")
        with pytest.raises(ValueError, match="empty or contains only unsafe"):
            sanitize_directory_name("///")
