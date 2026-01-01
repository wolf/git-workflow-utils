"""Direnv integration utilities."""

import shutil
import subprocess
from pathlib import Path


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
