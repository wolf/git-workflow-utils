"""Path and repository resolution utilities."""

import re
from pathlib import Path


def resolve_path(path: str | Path | None = None) -> Path:
    """
    Resolve a path to an absolute Path object.

    Args:
        path: Path to resolve. If None or empty string, returns current directory.

    Returns:
        Absolute Path object

    Example:
        resolve_path("~/projects")  # Returns /home/user/projects
        resolve_path(None)           # Returns current directory
    """
    if not path:
        return Path.cwd()

    return Path(path).expanduser().resolve()


def is_absolute_repo_path(repo: Path) -> bool:
    """
    Check if the given path is an absolute path to a git repository.

    Args:
        repo: Path to check

    Returns:
        True if path is absolute, is a directory, and contains .git

    Example:
        if is_absolute_repo_path(Path("/path/to/repo")):
            print("Valid git repository")
    """
    return (
        repo.is_absolute()
        and repo.is_dir()
        and (repo / ".git").exists()
    )


def resolve_repo(repo: str | Path | None = None) -> Path:
    """
    Resolve a path to a Git repository and validate it exists.

    Args:
        repo: Path to repository. Uses current directory if not provided.

    Returns:
        Absolute path to the repository.

    Raises:
        AssertionError: If the path doesn't point to a valid Git repository.

    Example:
        repo = resolve_repo()  # Current directory
        repo = resolve_repo("~/projects/myrepo")
    """
    repo_path = resolve_path(repo)
    assert is_absolute_repo_path(repo_path)
    return repo_path


def sanitize_directory_name(name: str) -> str:
    r"""
    Sanitize a string to be safe for use as a directory name.

    Replaces unsafe filesystem characters with hyphens to ensure the string
    can be used as a directory name across different operating systems.

    Unsafe characters replaced with hyphens: / \ : * ? " < > |

    Additional transformations:
    - Multiple consecutive unsafe characters are collapsed to single hyphens
    - Leading and trailing hyphens are stripped

    Args:
        name: The string to sanitize (e.g., a git branch name)

    Returns:
        Sanitized string safe for directory names

    Raises:
        ValueError: If the result is empty after sanitization

    Example:
        >>> sanitize_directory_name("feature/foo")
        'feature-foo'
        >>> sanitize_directory_name("bug/fix:issue-123")
        'bug-fix-issue-123'
        >>> sanitize_directory_name("/leading-and-trailing/")
        'leading-and-trailing'
    """
    # Replace unsafe chars with hyphens and strip leading/trailing hyphens
    sanitized = re.sub(r'[/\\:*?"<>|]+', '-', name).strip('-')

    if not sanitized:
        raise ValueError(
            f"Name '{name}' is empty or contains only unsafe characters"
        )

    return sanitized
