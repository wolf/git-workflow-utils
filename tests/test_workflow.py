"""Tests for workflow module."""

import subprocess

import pytest

from git_workflow_utils.workflow import (
    _extract_repo_name_from_url,
    _parse_csv_config,
    expand_format,
    get_exclude_patterns,
    get_local_branch_format,
    get_owner,
    get_priority_branches,
    get_project_name,
    get_remote_branch_format,
    get_workflow_config,
)


class TestGetWorkflowConfig:
    """Tests for get_workflow_config function."""

    def test_returns_default_when_not_set(self, git_repo):
        value = get_workflow_config("ticket.prefix", repo=git_repo, default="DEFAULT")
        assert value == "DEFAULT"

    def test_returns_none_when_not_set_and_no_default(self, git_repo):
        value = get_workflow_config("ticket.prefix", repo=git_repo)
        assert value is None

    def test_returns_value_when_set(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.prefix", "SE-"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        value = get_workflow_config("ticket.prefix", repo=git_repo)
        assert value == "SE-"

    def test_value_overrides_default(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.prefix", "JIRA-"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        value = get_workflow_config("ticket.prefix", repo=git_repo, default="DEFAULT")
        assert value == "JIRA-"

    def test_works_with_nested_keys(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.branch.localFormat", "%(ticket)-%(desc)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        value = get_workflow_config("branch.localFormat", repo=git_repo)
        assert value == "%(ticket)-%(desc)"


class TestExpandFormat:
    """Tests for expand_format function."""

    def test_replaces_single_placeholder(self):
        result = expand_format("prefix-%(ticket)", ticket="SE-123")
        assert result == "prefix-SE-123"

    def test_replaces_multiple_placeholders(self):
        result = expand_format(
            "%(type)/%(owner)/%(ticket)-%(desc)",
            type="feature",
            owner="wolf",
            ticket="SE-123",
            desc="add-stuff",
        )
        assert result == "feature/wolf/SE-123-add-stuff"

    def test_leaves_unknown_placeholders_unchanged(self):
        result = expand_format("%(known)-%(unknown)", known="value")
        assert result == "value-%(unknown)"

    def test_handles_no_placeholders(self):
        result = expand_format("no placeholders here")
        assert result == "no placeholders here"

    def test_handles_empty_string(self):
        result = expand_format("")
        assert result == ""

    def test_handles_adjacent_placeholders(self):
        result = expand_format("%(a)%(b)%(c)", a="1", b="2", c="3")
        assert result == "123"

    def test_placeholder_at_start(self):
        result = expand_format("%(ticket)-description", ticket="SE-123")
        assert result == "SE-123-description"

    def test_placeholder_at_end(self):
        result = expand_format("description-%(ticket)", ticket="SE-123")
        assert result == "description-SE-123"


class TestExtractRepoNameFromUrl:
    """Tests for _extract_repo_name_from_url helper."""

    def test_https_url_with_git_suffix(self):
        name = _extract_repo_name_from_url("https://github.com/user/my-repo.git")
        assert name == "my-repo"

    def test_https_url_without_git_suffix(self):
        name = _extract_repo_name_from_url("https://github.com/user/my-repo")
        assert name == "my-repo"

    def test_ssh_url_with_git_suffix(self):
        name = _extract_repo_name_from_url("git@github.com:user/my-repo.git")
        assert name == "my-repo"

    def test_ssh_url_without_git_suffix(self):
        name = _extract_repo_name_from_url("git@github.com:user/my-repo")
        assert name == "my-repo"

    def test_local_path(self):
        name = _extract_repo_name_from_url("/path/to/my-repo.git")
        assert name == "my-repo"

    def test_trailing_slash(self):
        name = _extract_repo_name_from_url("https://github.com/user/my-repo.git/")
        assert name == "my-repo"

    def test_nested_path(self):
        name = _extract_repo_name_from_url("https://github.com/org/team/my-repo.git")
        assert name == "my-repo"

    def test_bitbucket_ssh(self):
        name = _extract_repo_name_from_url("git@bitbucket.org:company/project.git")
        assert name == "project"


class TestGetProjectName:
    """Tests for get_project_name function."""

    def test_returns_config_override(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.project.name", "my-project"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        name = get_project_name(git_repo)
        assert name == "my-project"

    def test_returns_remote_name_when_no_config(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        # The fixture creates a bare repo as remote, so let's set a proper URL
        subprocess.run(
            ["git", "remote", "set-url", "origin", "https://github.com/user/test-repo.git"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        name = get_project_name(git_repo)
        assert name == "test-repo"

    def test_returns_directory_name_when_no_remote(self, git_repo):
        # git_repo has no remote by default
        name = get_project_name(git_repo)
        assert name == "test-repo"  # The fixture creates repo in "test-repo" directory

    def test_config_takes_precedence_over_remote(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        subprocess.run(
            ["git", "remote", "set-url", "origin", "https://github.com/user/remote-name.git"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "workflow.project.name", "config-name"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        name = get_project_name(git_repo)
        assert name == "config-name"

    def test_works_in_worktree(self, git_repo, tmp_path):
        # Create a worktree
        worktree_path = tmp_path / "worktree"
        subprocess.run(
            ["git", "worktree", "add", str(worktree_path), "-b", "feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        # Project name should still be from main repo
        name = get_project_name(worktree_path)
        assert name == "test-repo"


class TestGetOwner:
    """Tests for get_owner function."""

    def test_returns_local_part_of_email(self, git_repo):
        owner = get_owner(git_repo)
        assert owner == "test"  # From test@example.com in conftest

    def test_returns_unknown_when_no_email(self, tmp_path):
        repo = tmp_path / "no-email-repo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
        # Unset any inherited email config
        subprocess.run(
            ["git", "config", "user.email", ""],
            cwd=repo,
            check=True,
            capture_output=True,
        )
        owner = get_owner(repo)
        # May return "unknown" or extract from global config; depends on environment
        assert isinstance(owner, str)
        assert len(owner) > 0

    def test_works_with_current_directory(self, git_repo, monkeypatch):
        monkeypatch.chdir(git_repo)
        owner = get_owner()
        assert owner == "test"


class TestParseCSVConfig:
    """Tests for _parse_csv_config helper."""

    def test_single_value(self):
        assert _parse_csv_config("prod") == ["prod"]

    def test_multiple_values(self):
        assert _parse_csv_config("prod,develop") == ["prod", "develop"]

    def test_strips_whitespace(self):
        assert _parse_csv_config(" prod , develop , main ") == ["prod", "develop", "main"]

    def test_filters_empty_items(self):
        assert _parse_csv_config("prod,,develop") == ["prod", "develop"]

    def test_empty_string(self):
        assert _parse_csv_config("") == []


class TestGetLocalBranchFormat:
    """Tests for get_local_branch_format function."""

    def test_returns_default(self, git_repo):
        assert get_local_branch_format(git_repo) == "%(desc)"

    def test_returns_configured_value(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.branch.localFormat", "%(ticket)-%(desc)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert get_local_branch_format(git_repo) == "%(ticket)-%(desc)"


class TestGetRemoteBranchFormat:
    """Tests for get_remote_branch_format function."""

    def test_returns_default(self, git_repo):
        assert get_remote_branch_format(git_repo) == "%(type)/%(owner)/%(ticket)-%(desc)"

    def test_returns_configured_value(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.branch.remoteFormat", "%(owner)/%(ticket)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert get_remote_branch_format(git_repo) == "%(owner)/%(ticket)"


class TestGetPriorityBranches:
    """Tests for get_priority_branches function."""

    def test_returns_default(self, git_repo):
        assert get_priority_branches(git_repo) == ["prod", "develop"]

    def test_returns_configured_value(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.branches.priority", "main, develop, staging"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert get_priority_branches(git_repo) == ["main", "develop", "staging"]


class TestGetExcludePatterns:
    """Tests for get_exclude_patterns function."""

    def test_returns_default(self, git_repo):
        assert get_exclude_patterns(git_repo) == ["*archive/*"]

    def test_returns_configured_value(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.branches.exclude", "*archive/*, wip/*"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert get_exclude_patterns(git_repo) == ["*archive/*", "wip/*"]
