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
    get_local_branches,
    get_remote_branches,
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


def get_branch_commit_message(branch: str, repo: Path | None = None) -> str | None:
    """
    Get the full commit message of the commit a branch points to.

    Args:
        branch: Branch name.
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Full commit message (subject + body) if the branch exists, otherwise None.
        To extract just the subject line: `msg.split("\n", 1)[0]`.

    """
    result = run_git("log", "-1", "--format=%B", branch, repo=repo, capture=True, check=False)
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
    if (msg := get_branch_commit_message(branch, repo=repo)) and (match := ticket_re.search(msg)):
        return match.group(1).upper()

    return None


def branch_matches_ticket(
    branch: str,
    ticket: str,
    check_details: bool = True,
    repo: Path | None = None,
) -> bool:
    """
    Check if a branch is associated with a given ticket.

    Searches the branch name for a case-insensitive substring match.
    When `check_details` is True, also searches the branch description,
    upstream tracking branch name, and commit message.

    This is the complement of `extract_ticket_from_branch`: that function
    discovers an unknown ticket from a branch; this one checks whether a
    branch is associated with a known ticket.

    Args:
        branch: Branch name to check.
        ticket: Ticket to search for (e.g., "SE-123").
        check_details: If True (default), also search description,
                       upstream, and commit message. Set to False for
                       remote branches where only the name is meaningful.
        repo: Optional repository path. If None, uses current directory.

    Returns:
        True if the branch is associated with the ticket.

    """
    ticket_upper = ticket.upper()

    if ticket_upper in branch.upper():
        return True

    if not check_details:
        return False

    if (desc := get_branch_description(branch, repo=repo)) and ticket_upper in desc.upper():
        return True

    if (upstream := get_branch_upstream(branch, repo=repo)) and ticket_upper in upstream.upper():
        return True

    if (msg := get_branch_commit_message(branch, repo=repo)) and ticket_upper in msg.upper():
        return True

    return False


def find_matching_branches(
    ticket: str,
    include_local: bool = True,
    include_remote: bool = False,
    deduplicate: bool = False,
    repo: Path | None = None,
) -> list[str]:
    """
    Find all branches matching a ticket.

    Searches local branches by name, description, upstream, and commit
    message. Searches remote branches by name only.

    Args:
        ticket: Ticket to search for (e.g., "SE-123").
        include_local: Search local branches (default True).
        include_remote: Search remote branches (default False).
        deduplicate: If True, removes remote branches that are upstreams
                     of matching local branches (since they represent the
                     same branch).
        repo: Optional repository path. If None, uses current directory.

    Returns:
        List of matching branch names (local branches first).

    """
    local_matches = [
        b for b in get_local_branches(repo=repo)
        if branch_matches_ticket(b, ticket, check_details=True, repo=repo)
    ] if include_local else []

    # For remote branches, only check the name (no description/upstream)
    remote_matches = [
        b for b in get_remote_branches(repo=repo)
        if branch_matches_ticket(b, ticket, check_details=False, repo=repo)
    ] if include_remote else []

    if deduplicate and local_matches and remote_matches:
        local_upstreams = {
            get_branch_upstream(b, repo=repo)
            for b in local_matches
        }
        local_upstreams.discard(None)
        remote_matches = [r for r in remote_matches if r not in local_upstreams]

    return local_matches + remote_matches
