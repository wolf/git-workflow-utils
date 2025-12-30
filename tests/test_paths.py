"""Tests for paths module."""

from pathlib import Path

import pytest

from git_workflow_utils.paths import is_absolute_repo_path, resolve_path, resolve_repo


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
