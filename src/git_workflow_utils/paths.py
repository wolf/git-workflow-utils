"""Path and repository resolution utilities."""

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
