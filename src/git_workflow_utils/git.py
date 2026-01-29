"""Core git operations."""

import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .direnv import direnv_allow
from .paths import resolve_repo
from .templates import apply_user_template, symlink_envrc_if_needed


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


def git_config(
    key: str,
    repo: Path | None = None,
    default: str | None = None,
) -> str | None:
    """
    Get a git config value.

    Args:
        key: Config key to retrieve (e.g., "user.name", "worktree.userTemplate.mode")
        repo: Optional repository path. If None, uses current directory.
        default: Default value if config key is not set.

    Returns:
        Config value if set, otherwise default.

    Example:
        mode = git_config("worktree.userTemplate.mode", default="link")
        email = git_config("user.email")
    """
    result = run_git("config", key, repo=repo, capture=True, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()
    return default


def git_config_list(
    key: str,
    repo: Path | None = None,
) -> set[str]:
    """
    Get all values for a multi-value git config key.

    Args:
        key: Config key to retrieve (e.g., "worktree.userTemplate.link")
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Set of config values, empty set if key is not set.

    Example:
        files = git_config_list("worktree.userTemplate.link")
        # Returns: {".envrc.local", ".ipython"}
    """
    result = run_git("config", "--get-all", key, repo=repo, capture=True, check=False)
    if result.returncode == 0 and result.stdout.strip():
        return set(result.stdout.strip().split("\n"))
    return set()


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
    - Set up .envrc from .envrc.sample (if present)
    - Allow direnv if .envrc exists (if direnv available)
    - Apply user templates from ~/.config/git/user-template/ (if configured)

    Note: This is for working copies, not bare repositories.

    Args:
        repo: Path to the working copy. Defaults to current directory.

    Example:
        initialize_repo()
        initialize_repo(Path("/path/to/new-worktree"))
    """
    repo_path = resolve_repo(repo)

    submodule_update(repo_path)

    envrc = symlink_envrc_if_needed(repo_path)
    if envrc:
        direnv_allow(envrc)

    apply_user_template(repo_path)


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


def get_git_common_dir(repo: Path | None = None) -> Path:
    """
    Get the common .git directory for the current repository.

    For worktrees, this returns the main repo's .git directory where shared
    data (branch configurations, refs, hooks) is stored. For regular repos,
    returns the .git directory.

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Path to the common .git directory (always absolute).

    """
    result = run_git("rev-parse", "--git-common-dir", repo=repo, capture=True)
    git_dir = Path(result.stdout.strip())

    # The output may be relative to the repo, not cwd
    if not git_dir.is_absolute():
        git_dir = resolve_repo(repo) / git_dir

    return git_dir.resolve()


def get_branches_with_descriptions(repo: Path | None = None) -> set[str]:
    """
    Find branches that have descriptions set.

    Uses `git config --get-regexp` to find all branch descriptions.

    Args:
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Set of branch names (without refs/heads/ prefix) that have descriptions.

    """
    import re

    result = run_git(
        "config", "--get-regexp", r"^branch\..*\.description$",
        repo=repo,
        capture=True,
        check=False,
    )

    if result.returncode != 0 or not result.stdout.strip():
        return set()

    # Output format: "branch.NAME.description VALUE"
    # Extract NAME from each line
    pattern = re.compile(r"^branch\.(.+)\.description\s")
    return {
        match.group(1)
        for line in result.stdout.splitlines()
        if (match := pattern.match(line))
    }


def get_branch_description(branch: str, repo: Path | None = None) -> str | None:
    """
    Get the description for a branch.

    Args:
        branch: Name of the branch.
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Branch description if set, otherwise None.

    Example:
        desc = get_branch_description("feature-branch")
        if desc:
            print(f"Branch description: {desc}")

    """
    result = run_git(
        "config", f"branch.{branch}.description",
        repo=repo,
        capture=True,
        check=False,
    )
    if result.returncode == 0 and (desc := result.stdout.strip()):
        return desc
    return None


def get_branch_upstream(branch: str, repo: Path | None = None) -> str | None:
    """
    Get the upstream tracking branch for a local branch.

    Args:
        branch: Name of the local branch.
        repo: Optional repository path. If None, uses current directory.

    Returns:
        Upstream branch in "remote/branch" format (e.g., "origin/main"),
        or None if no upstream is configured.

    Example:
        upstream = get_branch_upstream("feature")
        if upstream:
            print(f"Tracking: {upstream}")

    """
    # Get the remote name
    remote_result = run_git(
        "config", f"branch.{branch}.remote",
        repo=repo,
        capture=True,
        check=False,
    )
    if remote_result.returncode != 0 or not (remote := remote_result.stdout.strip()):
        return None

    # Get the merge ref
    merge_result = run_git(
        "config", f"branch.{branch}.merge",
        repo=repo,
        capture=True,
        check=False,
    )
    if merge_result.returncode != 0 or not (merge_ref := merge_result.stdout.strip()):
        return None

    # Convert refs/heads/branch to just branch
    branch_name = merge_ref.removeprefix("refs/heads/")
    return f"{remote}/{branch_name}"


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
