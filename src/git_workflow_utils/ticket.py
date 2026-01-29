"""
Ticket extraction and URL utilities.

Terminology:
    ticket: A full ticket identifier including prefix, e.g., "SE-1234", "JIRA-99", "#123".
            This follows the common pattern `[A-Z]+-\\d+` for Jira-style tickets or
            `#\\d+` for GitHub-style issues.

    bare ticket number: Just the numeric portion, e.g., "1234". When a bare number is
            provided, it can be expanded to a full ticket using a configured prefix.

"""

import re
from pathlib import Path

from .git import (
    current_branch,
    get_branch_description,
    get_branch_upstream,
    run_git,
)
from .workflow import expand_format, get_workflow_config


def normalize_ticket(ticket: str, repo: Path | None = None) -> str:
    """
    Normalize a ticket to its full form.

    If the input is all digits (a bare ticket number), prepends the configured
    prefix from `workflow.ticket.prefix`. If the input already contains
    non-digit characters, returns it unchanged.

    Args:
        ticket: A ticket or bare ticket number.
        repo: Repository path for reading `workflow.ticket.prefix` from config.
              If None, uses current directory.

    Returns:
        Full ticket. If the input is a bare number and no prefix is configured,
        returns the bare number unchanged.

    >>> normalize_ticket("SE-1234")
    'SE-1234'
    >>> normalize_ticket("JIRA-99")
    'JIRA-99'

    """
    if ticket.isdigit():
        prefix = get_workflow_config("ticket.prefix", repo=repo) or ""
        return f"{prefix}{ticket}"
    return ticket


def get_ticket_url(ticket: str, repo: Path | None = None) -> str | None:
    """
    Generate a URL for a ticket.

    Uses the `workflow.ticket.urlPattern` config to construct the URL.
    The pattern should contain `%(ticket)` as a placeholder.

    Args:
        ticket: A ticket or bare ticket number. Bare numbers are normalized
                using `workflow.ticket.prefix`.
        repo: Repository path for reading workflow config. If None, uses
              current directory.

    Returns:
        URL for the ticket, or None if `workflow.ticket.urlPattern` is not configured.

    """
    if not (pattern := get_workflow_config("ticket.urlPattern", repo=repo)):
        return None

    full_ticket = normalize_ticket(ticket, repo=repo)
    return expand_format(pattern, ticket=full_ticket)


def _get_first_commit_message(branch: str, repo: Path | None = None) -> str | None:
    """Get the commit message of the commit this branch points to."""
    result = run_git("log", "-1", "--format=%s", branch, repo=repo, capture=True, check=False)
    if result.returncode == 0 and (msg := result.stdout.strip()):
        return msg
    return None


def extract_ticket_from_branch(
    branch: str | None = None,
    repo: Path | None = None,
    pattern: str | None = None,
) -> str | None:
    """
    Extract a ticket from a branch.

    Searches for a ticket pattern in (order of precedence):
    1. Branch name
    2. Branch description
    3. Upstream tracking branch name
    4. First commit message on the branch

    The default pattern matches Jira-style (`SE-123`) and GitHub-style (`#123`)
    tickets. For other formats (e.g., Azure DevOps `AB#123`), provide a custom
    pattern with a single capture group for the full ticket.

    Args:
        branch: Branch name. If None, uses current branch.
        repo: Repository path. If None, uses current directory.
        pattern: Regex pattern for ticket matching. Should have a single
                 capture group for the full ticket.

    Returns:
        Ticket if found (uppercased), otherwise None.

    """
    if branch is None:
        if not (branch := current_branch(repo=repo)):
            return None

    # Default pattern matches common ticket formats:
    # - PROJ-123 (Jira-style)
    # - #123 (GitHub-style)
    ticket_re = re.compile(pattern or r"([A-Z]+-\d+|#\d+)", re.IGNORECASE)

    # 1. Search branch name
    if match := ticket_re.search(branch):
        return match.group(1).upper()

    # 2. Search branch description
    if (desc := get_branch_description(branch, repo=repo)) and (match := ticket_re.search(desc)):
        return match.group(1).upper()

    # 3. Search upstream branch name
    if (upstream := get_branch_upstream(branch, repo=repo)) and (match := ticket_re.search(upstream)):
        return match.group(1).upper()

    # 4. Search first commit message
    if (msg := _get_first_commit_message(branch, repo=repo)) and (match := ticket_re.search(msg)):
        return match.group(1).upper()

    return None
