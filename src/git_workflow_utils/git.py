"""Core git operations."""

import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .direnv import setup_envrc
from .paths import resolve_repo


def run_git(
    *args: str,
    repo: Path | None = None,
    check: bool = True,
    capture: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess:
    """
    Run a git command and return the result.

    Args:
        *args: Git command arguments (e.g., "status", "--porcelain")
        repo: Optional repository path. If None, runs in current directory.
        check: Whether to raise CalledProcessError on non-zero exit (default: True)
        capture: Whether to capture stdout/stderr (default: False)
        **kwargs: Additional arguments to pass to subprocess.run()

    Returns:
        CompletedProcess result

    Example:
        # Run in current directory
        run_git("status", "--short", capture=True)

        # Run in specific repo
        run_git("fetch", "--all", repo=Path("/path/to/repo"))
    """
    cmd = ["git"]

    # Add -C flag if repo is specified
    if repo is not None:
        cmd.extend(["-C", str(repo)])

    cmd.extend(args)

    # Set up capture if requested
    if capture:
        return subprocess.run(
            cmd, capture_output=True, text=True, check=check, **kwargs
        )

    return subprocess.run(cmd, check=check, **kwargs)


def current_branch(repo: Path | None = None) -> str:
    """
    Get the currently checked out branch name.

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Name of the current branch

    Example:
        branch = current_branch()
        branch = current_branch(Path("/path/to/repo"))
    """
    result = run_git("branch", "--show-current", repo=repo, capture=True)
    return result.stdout.strip()


def has_uncommitted_changes(repo: Path | None = None) -> bool:
    """
    Check if there are uncommitted changes in the working tree.

    This includes both tracked and untracked files.

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        True if there are uncommitted changes, False otherwise

    Example:
        if has_uncommitted_changes():
            print("You have uncommitted changes")
    """
    result = run_git("status", "--porcelain", repo=repo, capture=True)
    return bool(result.stdout.strip())


def fetch_all(repo: Path | None = None, *, quiet: bool = False) -> None:
    """
    Fetch all remotes, prune deleted refs, and update tags.

    Args:
        repo: Optional repository path. If None, uses current directory.
        quiet: If True, suppresses output (default: False)

    Example:
        fetch_all()
        fetch_all(Path("/path/to/repo"), quiet=True)
    """
    kwargs = {}
    if quiet:
        kwargs["stdout"] = subprocess.DEVNULL

    run_git(
        "fetch",
        "--prune",
        "--all",
        "--tags",
        "--recurse-submodules",
        repo=repo,
        **kwargs,
    )


def find_branches(
    pattern: str,
    repo: str | Path | None = None,
    remote_name: str = "origin",
) -> list[str]:
    """
    Find all branches (local and remote) matching a pattern.

    For simple names (no wildcards), searches for both local branch and
    remote_name/branch. For patterns with wildcards, passes through to git.
    Returns all matches - caller decides priority.

    Args:
        pattern: Branch name or pattern to search for.
        repo: Path to the Git repository. Defaults to current directory.
        remote_name: Name of the remote to search (default: "origin").

    Returns:
        List of matching branch names with ref prefixes removed
        (e.g., "main" instead of "refs/heads/main" or "origin/main"
        instead of "refs/remotes/origin/main").

    Example:
        branches = find_branches("feature")
        branches = find_branches("feature-*", repo=Path("/path/to/repo"))
    """
    repo_path = resolve_repo(repo)
    assert pattern

    # Check if pattern contains git wildcards
    has_wildcards = bool(set("*?[") & set(pattern))

    if has_wildcards:
        # Pattern search - use as-is
        patterns_to_search = [pattern]
    else:
        # Exact name - search local and remote
        patterns_to_search = [
            pattern,  # Local: feature
            f"{remote_name}/{pattern}",  # Remote: origin/feature
        ]

    all_matches = []
    for search_pattern in patterns_to_search:
        result = run_git(
            "branch",
            "--format=%(refname)",
            "--all",
            "--list",
            search_pattern,
            repo=repo_path,
            capture=True,
        )

        all_matches.extend([
            match.removeprefix("refs/heads/").removeprefix("refs/remotes/")
            for line in result.stdout.splitlines()
            if (match := line.strip())
        ])

    # Remove duplicates while preserving order
    seen = set()
    return [m for m in all_matches if not (m in seen or seen.add(m))]


def submodule_update(repo: str | Path | None = None) -> None:
    """
    Update submodules in the repository recursively.

    Args:
        repo: Path to the Git repository. Defaults to current directory.

    Example:
        submodule_update()
        submodule_update(Path("/path/to/repo"))
    """
    repo_path = resolve_repo(repo)

    run_git(
        "submodule",
        "update",
        "--init",
        "--recursive",
        repo=repo_path,
        stdout=subprocess.DEVNULL,
    )


def initialize_repo(repo: str | Path | None = None) -> None:
    """
    Initialize a working copy (worktree or fresh clone) with standard setup.

    This performs common post-clone/worktree setup tasks:
    - Initialize and update submodules recursively
    - Set up .envrc from .envrc.sample (if present and direnv available)

    Note: This is for working copies, not bare repositories.

    Args:
        repo: Path to the working copy. Defaults to current directory.

    Example:
        initialize_repo()
        initialize_repo(Path("/path/to/new-worktree"))
    """
    repo_path = resolve_repo(repo)

    submodule_update(repo_path)
    setup_envrc(repo_path)


def find_git_repos(
    root_dir: str | Path,
    include_worktrees: bool = True,
) -> Iterator[Path]:
    """
    Find all git repositories under root_dir.

    Yields repository paths (parent of .git file/directory).
    Handles both regular repos (.git directory) and worktrees (.git file).

    Args:
        root_dir: Root directory to search for git repositories
        include_worktrees: If False, exclude git worktrees (where .git is a file).
                          Default True for backward compatibility.

    Yields:
        Repository paths

    Example:
        # Find all repos including worktrees
        for repo in find_git_repos(Path.home() / "develop"):
            print(repo.name)

        # Find only main repos (exclude worktrees)
        for repo in find_git_repos(Path.home() / "develop", include_worktrees=False):
            print(repo.name)
    """
    for git_marker in Path(root_dir).rglob(".git"):
        # Yield directories (main repos) or files if worktrees requested
        # Skip exotic filesystem objects (devices, pipes, etc.)
        if git_marker.is_dir() or (include_worktrees and git_marker.is_file()):
            yield git_marker.parent


def filter_repos_by_ignore_file(
    repos: Iterable[Path],
    root_dir: str | Path,
    ignore_filename: str,
) -> Iterator[Path]:
    """
    Filter repositories based on gitignore-style ignore files.

    Reads ignore files hierarchically (like .gitignore) and filters
    the repository list using gitignore-style patterns. Supports:
    - Simple patterns: repo-name
    - Wildcards: archived-*, */node_modules
    - Path patterns: third-party/*, wolf/*/old
    - Negation: !important-repo
    - Comments: # lines starting with hash

    Ignore files are checked hierarchically from root_dir upward,
    with patterns in deeper directories taking precedence.

    Args:
        repos: Iterator or list of repository paths to filter
        root_dir: Root directory that was searched (used to find ignore files)
        ignore_filename: Name of ignore file to look for (e.g., ".journalignore", ".deployignore")

    Yields:
        Repository paths that are not ignored

    Example:
        # Filter for daily work summary
        repos = find_git_repos(Path.home() / "develop", include_worktrees=False)
        active_repos = filter_repos_by_ignore_file(repos, Path.home() / "develop", ".journalignore")
        for repo in active_repos:
            print(f"Active repo: {repo.name}")
    """
    import pathspec

    root_dir = Path(root_dir).resolve()

    # Walk up from root_dir to find all ignore files
    # (We'll read them in order from root down for proper precedence)
    ignore_files = []
    for parent in [root_dir] + list(root_dir.parents):
        ignore_file = parent / ignore_filename
        if ignore_file.exists():
            ignore_files.append(ignore_file)

    # Read in reverse order (root first) so deeper files override
    ignore_files.reverse()

    # Build combined pathspec from all ignore files
    patterns = []
    for ignore_file in ignore_files:
        with open(ignore_file) as f:
            patterns.extend(f.read().splitlines())

    # Create pathspec matcher (handles gitignore syntax)
    spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    # Filter repos
    for repo in repos:
        # Get path relative to root_dir for matching
        try:
            rel_path = repo.relative_to(root_dir)
        except ValueError:
            # Repo is outside root_dir, don't filter it
            yield repo
            continue

        # Check if this repo path matches any ignore pattern
        # pathspec returns True if path matches (should be ignored)
        if not spec.match_file(str(rel_path)):
            yield repo


def user_email_in_this_working_copy(repo: str | Path | None = None) -> str | None:
    """
    Get the configured user email for this working copy.

    Args:
        repo: Path to working copy. Defaults to current directory.

    Returns:
        Configured user.email, or None if not configured

    Example:
        email = user_email_in_this_working_copy(Path("/path/to/repo"))
        if email:
            print(f"Author: {email}")
    """
    repo = resolve_repo(repo)

    try:
        result = run_git("config", "user.email", repo=repo, capture=True)
        email = result.stdout.strip()
        return email if email else None
    except subprocess.CalledProcessError:
        return None


def get_commits(
    repo: str | Path | None = None,
    since: str | None = None,
    author_email: str | None = None,
) -> Iterator[tuple[str, str]]:
    """
    Get commits from repository, optionally filtered by time and author.

    Yields (commit_hash, summary) tuples for commits matching the criteria.

    Args:
        repo: Path to working copy. Defaults to current directory.
        since: Time range (e.g., 'midnight', '24 hours ago', '2025-12-30 08:00')
        author_email: Filter by author email

    Yields:
        Tuples of (commit_hash, summary)

    Example:
        for hash, summary in get_commits(since="midnight", author_email="you@example.com"):
            print(f"{hash[:7]} - {summary}")
    """
    repo = resolve_repo(repo)

    args = ["log", "--format=%H%x00%s", "--all"]

    if since:
        args.append(f"--since={since}")

    if author_email:
        args.append(f"--author={author_email}")

    try:
        result = run_git(*args, repo=repo, capture=True)

        for line in result.stdout.strip().split("\n"):
            if line:
                hash_part, summary = line.split("\x00", 1)
                yield (hash_part, summary)

    except subprocess.CalledProcessError:
        return
