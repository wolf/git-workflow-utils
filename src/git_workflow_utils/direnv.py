"""Direnv integration utilities."""

import shutil
import subprocess
from pathlib import Path

from .paths import resolve_repo


def is_direnv_available() -> bool:
    """
    Check if direnv command is available in PATH.

    Returns:
        True if direnv is installed and available, False otherwise.

    Example:
        if is_direnv_available():
            setup_envrc()
    """
    return shutil.which("direnv") is not None


def direnv_allow(envrc: Path) -> None:
    """
    Allow direnv to load the specified .envrc file.

    Args:
        envrc: Path to the .envrc file.

    Example:
        direnv_allow(Path("/path/to/repo/.envrc"))
    """
    if envrc.is_file() and envrc.name == ".envrc" and is_direnv_available():
        subprocess.run(
            ["direnv", "allow", str(envrc)],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def setup_envrc(repo: str | Path | None = None) -> None:
    """
    Discover, possibly create, and allow `.envrc`.

    If .envrc.sample exists but .envrc doesn't, creates a symlink.
    Then runs direnv allow if .envrc exists.

    Args:
        repo: Path to the repository. Defaults to current directory.

    Example:
        setup_envrc()
        setup_envrc(Path("/path/to/repo"))
    """
    # Early exit if direnv not available - don't even resolve repo
    if not is_direnv_available():
        return

    repo_path = resolve_repo(repo)

    envrc_sample = repo_path / ".envrc.sample"
    envrc = repo_path / ".envrc"

    if envrc_sample.exists() and not envrc.exists():
        envrc.symlink_to(envrc_sample.name)

    if envrc.exists():
        direnv_allow(envrc)
