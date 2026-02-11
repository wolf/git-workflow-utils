"""Tests for ticket module."""

import subprocess

import pytest

from git_workflow_utils.ticket import (
    branch_matches_ticket,
    extract_ticket_from_branch,
    find_matching_branches,
    get_branch_commit_message,
    get_ticket_url,
    normalize_ticket,
)


class TestNormalizeTicket:
    """Tests for normalize_ticket function."""

    def test_returns_full_ticket_unchanged(self, git_repo):
        assert normalize_ticket("SE-1234", git_repo) == "SE-1234"
        assert normalize_ticket("JIRA-99", git_repo) == "JIRA-99"
        assert normalize_ticket("#123", git_repo) == "#123"

    def test_expands_bare_number_with_prefix(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.prefix", "SE-"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert normalize_ticket("1234", git_repo) == "SE-1234"

    def test_returns_bare_number_when_no_prefix_configured(self, git_repo):
        # No prefix configured
        assert normalize_ticket("1234", git_repo) == "1234"

    def test_is_idempotent(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.prefix", "SE-"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        # Normalizing twice gives same result
        once = normalize_ticket("1234", git_repo)
        twice = normalize_ticket(once, git_repo)
        assert once == twice == "SE-1234"


class TestGetTicketUrl:
    """Tests for get_ticket_url function."""

    def test_returns_none_when_no_pattern_configured(self, git_repo):
        url = get_ticket_url("SE-1234", git_repo)
        assert url is None

    def test_returns_url_with_pattern(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.urlPattern", "https://jira.example.com/browse/%(ticket)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        url = get_ticket_url("SE-1234", git_repo)
        assert url == "https://jira.example.com/browse/SE-1234"

    def test_normalizes_bare_ticket_number(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.prefix", "SE-"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "workflow.ticket.urlPattern", "https://jira.example.com/browse/%(ticket)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        url = get_ticket_url("1234", git_repo)
        assert url == "https://jira.example.com/browse/SE-1234"

    def test_github_style_pattern(self, git_repo):
        subprocess.run(
            ["git", "config", "workflow.ticket.urlPattern", "https://github.com/org/repo/issues/%(ticket)"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        url = get_ticket_url("#456", git_repo)
        assert url == "https://github.com/org/repo/issues/#456"


class TestExtractTicketFromBranch:
    """Tests for extract_ticket_from_branch function."""

    def test_extracts_from_branch_name(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-123-add-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("feature/SE-123-add-stuff", git_repo)
        assert ticket == "SE-123"

    def test_extracts_from_branch_description(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "my-feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-feature.description", "Working on SE-456"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("my-feature", git_repo)
        assert ticket == "SE-456"

    def test_extracts_from_upstream_name(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        # Create a local branch with different name than remote
        subprocess.run(
            ["git", "checkout", "-b", "local-name"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        # Push to remote with ticket in name
        subprocess.run(
            ["git", "push", "-u", "origin", "local-name:feature/SE-789-remote-name"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("local-name", git_repo)
        assert ticket == "SE-789"

    def test_extracts_from_commit_message(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "plain-branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("new feature")
        subprocess.run(["git", "add", "feature.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "SE-999: Add new feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("plain-branch", git_repo)
        assert ticket == "SE-999"

    def test_returns_none_when_no_ticket_found(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "plain-branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("plain-branch", git_repo)
        assert ticket is None

    def test_uses_current_branch_when_none_specified(self, git_repo, monkeypatch):
        subprocess.run(
            ["git", "checkout", "-b", "feature/JIRA-100-something"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        monkeypatch.chdir(git_repo)
        ticket = extract_ticket_from_branch()
        assert ticket == "JIRA-100"

    def test_extracts_github_style_ticket(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "fix-#42"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("fix-#42", git_repo)
        assert ticket == "#42"

    def test_returns_uppercase_ticket(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/se-123-lowercase"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("feature/se-123-lowercase", git_repo)
        assert ticket == "SE-123"

    def test_custom_pattern(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/BUG123-fix"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        # Default pattern won't match BUG123 (no hyphen)
        assert extract_ticket_from_branch("feature/BUG123-fix", git_repo) is None
        # Custom pattern matches
        ticket = extract_ticket_from_branch(
            "feature/BUG123-fix",
            git_repo,
            pattern=r"(BUG\d+)",
        )
        assert ticket == "BUG123"

    def test_extracts_ticket_from_trailer(self, git_repo):
        """Structured Ticket trailer is found in description."""
        subprocess.run(
            ["git", "checkout", "-b", "my-work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-work.description", "Ticket: SE-777\nRemote: feature/wolf/SE-777-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("my-work", git_repo)
        assert ticket == "SE-777"

    def test_trailer_preferred_over_regex(self, git_repo):
        """Structured Ticket trailer takes precedence over regex match in description."""
        subprocess.run(
            ["git", "checkout", "-b", "my-work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        # Description has a Ticket trailer and also mentions another ticket in prose
        subprocess.run(
            ["git", "config", "branch.my-work.description",
             "Fix for SE-999 regression\n\nTicket: SE-888"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("my-work", git_repo)
        assert ticket == "SE-888"

    def test_branch_name_takes_precedence(self, git_repo):
        """When ticket is in multiple places, branch name wins."""
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-111-in-name"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.feature/SE-111-in-name.description", "SE-222 in description"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        ticket = extract_ticket_from_branch("feature/SE-111-in-name", git_repo)
        assert ticket == "SE-111"


class TestGetBranchCommitMessage:
    """Tests for get_branch_commit_message function."""

    def test_returns_commit_message(self, git_repo):
        msg = get_branch_commit_message("main", git_repo)
        assert msg == "Initial commit"

    def test_returns_full_message_with_body(self, git_repo):
        (git_repo / "file.txt").write_text("content")
        subprocess.run(["git", "add", "file.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Subject line\n\nBody paragraph here."],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        msg = get_branch_commit_message("main", git_repo)
        assert "Subject line" in msg
        assert "Body paragraph here." in msg

    def test_returns_none_for_nonexistent_branch(self, git_repo):
        msg = get_branch_commit_message("nonexistent", git_repo)
        assert msg is None


class TestBranchMatchesTicket:
    """Tests for branch_matches_ticket function."""

    def test_matches_ticket_in_branch_name(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-123-add-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("feature/SE-123-add-stuff", "SE-123", repo=git_repo)

    def test_case_insensitive(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/se-123-add-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("feature/se-123-add-stuff", "SE-123", repo=git_repo)

    def test_no_match_returns_false(self, git_repo):
        assert not branch_matches_ticket("main", "SE-999", repo=git_repo)

    def test_matches_ticket_in_description(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "my-feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-feature.description", "Working on SE-456"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("my-feature", "SE-456", repo=git_repo)

    def test_matches_ticket_in_upstream(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        subprocess.run(
            ["git", "checkout", "-b", "local-name"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "local-name:feature/SE-789-remote"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("local-name", "SE-789", repo=git_repo)

    def test_matches_ticket_in_commit_message(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "plain-branch"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        (git_repo / "feature.txt").write_text("new feature")
        subprocess.run(["git", "add", "feature.txt"], cwd=git_repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "SE-999: Add new feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("plain-branch", "SE-999", repo=git_repo)

    def test_matches_ticket_via_trailer(self, git_repo):
        """Structured Ticket trailer is used for matching."""
        subprocess.run(
            ["git", "checkout", "-b", "my-work"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-work.description", "Ticket: SE-456\nRemote: feature/wolf/SE-456-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert branch_matches_ticket("my-work", "SE-456", repo=git_repo)

    def test_check_details_false_skips_description(self, git_repo):
        """With check_details=False, only branch name is checked."""
        subprocess.run(
            ["git", "checkout", "-b", "my-feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-feature.description", "Working on SE-456"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        assert not branch_matches_ticket("my-feature", "SE-456", check_details=False, repo=git_repo)


class TestFindMatchingBranches:
    """Tests for find_matching_branches function."""

    def test_finds_local_branch_by_name(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-123-stuff"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        matches = find_matching_branches("SE-123", repo=git_repo)
        assert "feature/SE-123-stuff" in matches

    def test_returns_empty_when_no_match(self, git_repo):
        matches = find_matching_branches("SE-999", repo=git_repo)
        assert matches == []

    def test_finds_remote_branches(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-100-remote"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "feature/SE-100-remote"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        matches = find_matching_branches(
            "SE-100", include_remote=True, repo=git_repo,
        )
        assert "feature/SE-100-remote" in matches
        assert any("origin/" in m for m in matches)

    def test_deduplicates_remotes(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-200-dedup"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "feature/SE-200-dedup"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        matches = find_matching_branches(
            "SE-200", include_remote=True, deduplicate=True, repo=git_repo,
        )
        # Local branch should be present
        assert "feature/SE-200-dedup" in matches
        # Remote that is upstream of local should be removed
        assert "origin/feature/SE-200-dedup" not in matches

    def test_include_local_false(self, git_repo_with_remote):
        git_repo, _ = git_repo_with_remote
        subprocess.run(
            ["git", "checkout", "-b", "feature/SE-300-local"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "push", "origin", "feature/SE-300-local"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        matches = find_matching_branches(
            "SE-300", include_local=False, include_remote=True, repo=git_repo,
        )
        assert "feature/SE-300-local" not in matches
        assert "origin/feature/SE-300-local" in matches

    def test_finds_branch_by_description(self, git_repo):
        subprocess.run(
            ["git", "checkout", "-b", "my-feature"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "branch.my-feature.description", "Ticket: SE-400"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        matches = find_matching_branches("SE-400", repo=git_repo)
        assert "my-feature" in matches
