"""Workflow configuration and format string utilities."""

import re
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .git import git_config, run_git, user_email_in_this_working_copy
from .paths import resolve_repo


def get_workflow_config(
    key: str,
    repo: Path | None = None,
    default: str | None = None,
) -> str | None:
    """
    Get a workflow configuration value.

    Reads from git config under the `workflow.*` namespace.

    Args:
        key: Config key without the "workflow." prefix (e.g., "ticket.prefix").
        repo: Optional repository path. If None, uses current directory.
        default: Default value if config key is not set.

    Returns:
        Config value if set, otherwise default.

    Example:
        prefix = get_workflow_config("ticket.prefix", default="")
        url_pattern = get_workflow_config("ticket.urlPattern")

    """
    return git_config(f"workflow.{key}", repo=repo, default=default)


def expand_format(format_string: str, **placeholders: str) -> str:
    """
    Expand a format string with named placeholders.

    Replaces `%(name)` patterns with corresponding values from placeholders.
    Unknown placeholders are left unchanged.

    Args:
        format_string: String containing `%(name)` placeholders.
        **placeholders: Keyword arguments mapping placeholder names to values.

    Returns:
        Format string with placeholders replaced.

    Example:
        expand_format("%(type)/%(owner)/%(ticket)", type="feature", owner="wolf", ticket="SE-123")
        # Returns: "feature/wolf/SE-123"

    """
    def replace(match: re.Match) -> str:
        name = match.group(1)
        return placeholders.get(name, match.group(0))

    return re.sub(r"%\((\w+)\)", replace, format_string)


def get_owner(repo: Path | None = None) -> str:
    """
    Get the owner name for workflow format placeholders.

    Extracts the local part of the configured `user.email` (before the `@`).
    Returns `"unknown"` if no email is configured.

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Owner name derived from git user.email.

    """
    if email := user_email_in_this_working_copy(repo=repo):
        return email.split("@")[0]
    return "unknown"


def _extract_repo_name_from_url(url: str) -> str | None:
    """
    Extract repository name from a git remote URL.

    Handles various URL formats:
    - HTTPS: https://github.com/user/repo.git
    - SSH: git@github.com:user/repo.git
    - Local: /path/to/repo.git

    """
    url = url.strip().rstrip("/")

    # Handle SSH-style URLs (git@host:path) by converting to parseable form
    if "@" in url and "://" not in url:
        # git@github.com:user/repo.git → extract the path part after ':'
        if ":" in url:
            url = url.split(":", 1)[1]

    # For standard URLs, extract path component
    parsed = urlsplit(url)
    path = parsed.path if parsed.scheme else url

    # Use PurePosixPath to get the final component, stripping .git suffix
    name = PurePosixPath(path).stem if path.endswith(".git") else PurePosixPath(path).name
    return name if name else None


def get_project_name(repo: Path | None = None) -> str | None:
    """
    Get the project name for a repository.

    Resolution cascade:
    1. `workflow.project.name` config (explicit override)
    2. Leaf of remote origin URL (without .git suffix)
    3. Directory name containing the main clone (via git-common-dir)

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Project name, or None if it cannot be determined.

    Example:
        name = get_project_name()
        # Might return "siloc" for a repo at ~/develop/dmp/siloc

    """
    # 1. Check config override
    if config_name := get_workflow_config("project.name", repo=repo):
        return config_name

    # 2. Try remote origin URL
    result = run_git("remote", "get-url", "origin", repo=repo, capture=True, check=False)
    if result.returncode == 0 and (url := result.stdout.strip()):
        if name := _extract_repo_name_from_url(url):
            return name

    # 3. Fall back to directory name via git-common-dir
    # The output may be relative (e.g., ".git" or "../../.git/worktrees/foo"),
    # in which case it's relative to the repo path, not cwd.
    result = run_git("rev-parse", "--git-common-dir", repo=repo, capture=True, check=False)
    if result.returncode == 0 and (git_dir := result.stdout.strip()):
        git_path = Path(git_dir)
        if not git_path.is_absolute():
            git_path = resolve_repo(repo) / git_path
        return git_path.resolve().parent.name

    return None
