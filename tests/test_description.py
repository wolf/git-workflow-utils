"""Tests for description module."""

from git_workflow_utils.description import (
    BranchDescription,
    build_branch_description,
    format_branch_description,
    parse_branch_description,
)


class TestBranchDescription:
    """Tests for BranchDescription dataclass."""

    def test_empty_description(self):
        desc = BranchDescription()
        assert desc.summary == ""
        assert desc.trailers == {}

    def test_get_returns_first_value(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123", "SE-456"]})
        assert desc.get("Ticket") == "SE-123"

    def test_get_returns_none_when_missing(self):
        desc = BranchDescription()
        assert desc.get("Ticket") is None

    def test_get_all_returns_all_values(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123", "SE-456"]})
        assert desc.get_all("Ticket") == ["SE-123", "SE-456"]

    def test_get_all_returns_empty_list_when_missing(self):
        desc = BranchDescription()
        assert desc.get_all("Ticket") == []

    def test_get_is_case_insensitive(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123"]})
        assert desc.get("ticket") == "SE-123"
        assert desc.get("TICKET") == "SE-123"

    def test_get_all_is_case_insensitive(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123", "SE-456"]})
        assert desc.get_all("ticket") == ["SE-123", "SE-456"]

    def test_replace_sets_single_value(self):
        desc = BranchDescription()
        desc.replace("Remote", "feature/wolf/SE-123")
        assert desc.get("Remote") == "feature/wolf/SE-123"

    def test_replace_overwrites_existing(self):
        desc = BranchDescription(trailers={"Remote": ["old-branch"]})
        desc.replace("Remote", "new-branch")
        assert desc.get("Remote") == "new-branch"
        assert desc.get_all("Remote") == ["new-branch"]

    def test_replace_normalizes_key_casing(self):
        desc = BranchDescription(trailers={"remote": ["old"]})
        desc.replace("Remote", "new")
        assert "remote" not in desc.trailers
        assert desc.get("Remote") == "new"

    def test_add_appends_to_existing(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123"]})
        desc.add("Ticket", "SE-456")
        assert desc.get_all("Ticket") == ["SE-123", "SE-456"]

    def test_add_creates_new_key(self):
        desc = BranchDescription()
        desc.add("Ticket", "SE-123")
        assert desc.get("Ticket") == "SE-123"

    def test_add_preserves_existing_key_casing(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123"]})
        desc.add("ticket", "SE-456")
        assert "Ticket" in desc.trailers
        assert "ticket" not in desc.trailers

    def test_tickets_property(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123", "SE-456"]})
        assert desc.tickets == ["SE-123", "SE-456"]

    def test_tickets_property_empty(self):
        desc = BranchDescription()
        assert desc.tickets == []

    def test_remote_property(self):
        desc = BranchDescription(trailers={"Remote": ["feature/wolf/SE-123"]})
        assert desc.remote == "feature/wolf/SE-123"

    def test_remote_property_none(self):
        desc = BranchDescription()
        assert desc.remote is None

    def test_pr_property(self):
        desc = BranchDescription(trailers={"PR": ["https://example.com/pr/42"]})
        assert desc.pr == "https://example.com/pr/42"

    def test_pr_property_none(self):
        desc = BranchDescription()
        assert desc.pr is None


class TestParseBranchDescription:
    """Tests for parse_branch_description function."""

    def test_parse_empty_string(self):
        desc = parse_branch_description("")
        assert desc.summary == ""
        assert desc.trailers == {}

    def test_parse_summary_only(self):
        desc = parse_branch_description("Just a plain text description.")
        assert desc.summary == "Just a plain text description."
        assert desc.trailers == {}

    def test_parse_multiline_summary_only(self):
        text = "First line.\n\nSecond paragraph with more detail."
        desc = parse_branch_description(text)
        assert desc.summary == text
        assert desc.trailers == {}

    def test_parse_trailers_only(self):
        text = "Ticket: SE-123\nRemote: feature/wolf/SE-123-stuff"
        desc = parse_branch_description(text)
        assert desc.summary == ""
        assert desc.tickets == ["SE-123"]
        assert desc.remote == "feature/wolf/SE-123-stuff"

    def test_parse_summary_and_trailers(self):
        text = "Add caching for API responses.\n\nTicket: SE-123\nType: feature"
        desc = parse_branch_description(text)
        assert desc.summary == "Add caching for API responses."
        assert desc.tickets == ["SE-123"]
        assert desc.get("Type") == "feature"

    def test_parse_multiple_tickets(self):
        text = "Ticket: SE-123\nTicket: SE-456\nRemote: branch-name"
        desc = parse_branch_description(text)
        assert desc.tickets == ["SE-123", "SE-456"]

    def test_parse_preserves_key_case(self):
        text = "Created-from: prod\nPR: https://example.com/pr/1"
        desc = parse_branch_description(text)
        assert "Created-from" in desc.trailers
        assert "PR" in desc.trailers

    def test_parse_strips_whitespace(self):
        text = "  Ticket: SE-123  \n  Remote: branch-name  "
        desc = parse_branch_description(text)
        assert desc.tickets == ["SE-123"]
        assert desc.remote == "branch-name"

    def test_parse_extra_blank_lines(self):
        text = "Summary here.\n\n\nTicket: SE-123\nRemote: branch"
        desc = parse_branch_description(text)
        assert desc.summary == "Summary here."
        assert desc.tickets == ["SE-123"]

    def test_parse_legacy_format(self):
        """The current format written by git-branch-create-for-ticket."""
        text = "Ticket: SE-123\nRemote: feature/wolf/SE-123-my-feature"
        desc = parse_branch_description(text)
        assert desc.summary == ""
        assert desc.tickets == ["SE-123"]
        assert desc.remote == "feature/wolf/SE-123-my-feature"

    def test_parse_body_text_not_confused_with_trailers(self):
        """Non-trailer text between summary and trailer-like lines."""
        text = "Summary.\n\nThis line has: a colon but is body text.\n\nTicket: SE-123"
        desc = parse_branch_description(text)
        assert desc.tickets == ["SE-123"]
        assert "colon" in desc.summary

    def test_roundtrip(self):
        original = BranchDescription(
            summary="Add new feature.",
            trailers={
                "Ticket": ["SE-123", "SE-456"],
                "Remote": ["feature/wolf/SE-123-stuff"],
                "Type": ["feature"],
            },
        )
        text = format_branch_description(original)
        parsed = parse_branch_description(text)
        assert parsed.summary == original.summary
        assert parsed.trailers == original.trailers


class TestFormatBranchDescription:
    """Tests for format_branch_description function."""

    def test_format_empty(self):
        desc = BranchDescription()
        assert format_branch_description(desc) == ""

    def test_format_summary_only(self):
        desc = BranchDescription(summary="Just a summary.")
        assert format_branch_description(desc) == "Just a summary."

    def test_format_trailers_only(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123"], "Remote": ["branch"]})
        assert format_branch_description(desc) == "Ticket: SE-123\nRemote: branch"

    def test_format_full(self):
        desc = BranchDescription(
            summary="Add feature.",
            trailers={"Ticket": ["SE-123"], "Type": ["feature"]},
        )
        expected = "Add feature.\n\nTicket: SE-123\nType: feature"
        assert format_branch_description(desc) == expected

    def test_format_multiple_values(self):
        desc = BranchDescription(trailers={"Ticket": ["SE-123", "SE-456"]})
        assert format_branch_description(desc) == "Ticket: SE-123\nTicket: SE-456"


class TestBuildBranchDescription:
    """Tests for build_branch_description function."""

    def test_build_minimal(self):
        desc = build_branch_description(tickets="SE-123")
        assert desc.tickets == ["SE-123"]
        assert desc.summary == ""

    def test_build_full(self):
        desc = build_branch_description(
            tickets="SE-123",
            remote="feature/wolf/SE-123-stuff",
            branch_type="feature",
            author="wolf",
            created_from="prod",
            summary="Add caching.",
        )
        assert desc.summary == "Add caching."
        assert desc.tickets == ["SE-123"]
        assert desc.remote == "feature/wolf/SE-123-stuff"
        assert desc.get("Type") == "feature"
        assert desc.get("Author") == "wolf"
        assert desc.get("Created-from") == "prod"

    def test_build_multiple_tickets(self):
        desc = build_branch_description(tickets=["SE-123", "SE-456"])
        assert desc.tickets == ["SE-123", "SE-456"]

    def test_build_no_args(self):
        desc = build_branch_description()
        assert desc.summary == ""
        assert desc.trailers == {}
