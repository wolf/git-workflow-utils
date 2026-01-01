"""Template and file setup utilities for repository initialization."""

import shutil
from pathlib import Path

from .paths import resolve_repo


def symlink_envrc_if_needed(
    repo: str | Path | None = None,
    template: str = ".envrc.sample",
) -> Path | None:
    """
    Create .envrc symlink from template if needed.

    If the template file exists and .envrc doesn't, creates a relative symlink.
    This handles the common pattern of .envrc.sample → .envrc (or similar).

    Args:
        repo: Path to the repository. Defaults to current directory.
        template: Template filename to symlink from (default: .envrc.sample).
                 Should be a filename, not a full path.

    Returns:
        Path to .envrc if it exists (whether just created or pre-existing),
        None if .envrc doesn't exist and cannot be created.

    Example:
        # Standard usage
        envrc = symlink_envrc_if_needed()

        # Custom template name
        envrc = symlink_envrc_if_needed(template=".envrc.template")

        # Specific repo
        envrc = symlink_envrc_if_needed(Path("/path/to/repo"))
    """
    repo_path = resolve_repo(repo)
    template_path = repo_path / template
    envrc = repo_path / ".envrc"

    if envrc.exists():
        return envrc

    if template_path.exists():
        envrc.symlink_to(template)
        return envrc


def apply_user_template(
    repo: str | Path | None = None,
    template_path: Path | None = None,
) -> None:
    """
    Apply user template to repository working directory.

    Copies or symlinks files from a user template directory into the
    repository. This is useful for user-specific configuration files
    that should exist in every worktree but are gitignored (.envrc.local,
    .ipython/, .helix/, etc.).

    Template location priority:
    1. template_path parameter (if provided)
    2. git config worktree.userTemplate.path
    3. ~/.config/git/user-template/ (default)

    The mode (copy vs symlink) is controlled by git config:
    - git config worktree.userTemplate.mode [link|copy]
    - REQUIRED if template directory exists

    Per-file overrides:
    - git config --add worktree.userTemplate.link "filename"
    - git config --add worktree.userTemplate.copy "filename"

    Args:
        repo: Path to the repository. Defaults to current directory.
        template_path: Optional explicit path to template directory.
                      Overrides default template discovery.

    Raises:
        RuntimeError: If template exists but mode is not configured.

    Example:
        # Use default ~/.config/git/user-template/
        apply_user_template()

        # Use specific template directory
        apply_user_template(template_path=Path("~/.config/git/templates/python"))

        # Setup (one-time)
        git config --global worktree.userTemplate.mode link
        mkdir -p ~/.config/git/user-template
        echo 'export MY_VAR=value' > ~/.config/git/user-template/.envrc.local

        # Per-project template (if you need different templates per project)
        git config worktree.userTemplate.path ~/.config/git/templates/python
    """
    from .git import git_config, git_config_list

    repo_path = resolve_repo(repo)

    # Find template directory
    template_dir = _find_template_directory(repo_path, template_path)
    if not template_dir:
        return  # No template configured, nothing to do

    # Get mode configuration
    mode = git_config("worktree.userTemplate.mode", repo=repo_path)
    if not mode:
        raise RuntimeError(
            f"Template directory exists at {template_dir} but worktree.userTemplate.mode "
            "is not configured. Set it with:\n"
            "  git config --global worktree.userTemplate.mode [link|copy]"
        )

    if mode not in {"link", "copy"}:
        raise RuntimeError(
            f"Invalid worktree.userTemplate.mode: {mode}. Must be 'link' or 'copy'."
        )

    # Get per-file overrides (git_config_list already returns set)
    link_files = git_config_list("worktree.userTemplate.link", repo=repo_path)
    copy_files = git_config_list("worktree.userTemplate.copy", repo=repo_path)

    # Apply template
    for item in template_dir.iterdir():
        target = repo_path / item.name

        # Skip if target already exists
        if target.exists():
            continue

        # Determine mode for this item
        item_mode = mode
        if item.name in link_files:
            item_mode = "link"
        elif item.name in copy_files:
            item_mode = "copy"

        # Apply based on mode
        if item_mode == "link":
            target.symlink_to(item)
        else:  # copy
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)


def _find_template_directory(
    repo_path: Path,
    explicit_path: Path | None,
) -> Path | None:
    """
    Find the template directory to use.

    Priority:
    1. Explicit path parameter
    2. git config worktree.userTemplate.path
    3. ~/.config/git/user-template/ (default)
    """
    from .git import git_config

    # Priority 1: Explicit path parameter
    if explicit_path:
        expanded = explicit_path.expanduser().resolve()
        return expanded if expanded.exists() and expanded.is_dir() else None

    # Priority 2: Git config
    config_path_str = git_config("worktree.userTemplate.path", repo=repo_path)
    if config_path_str:
        config_path = Path(config_path_str).expanduser().resolve()
        if config_path.exists() and config_path.is_dir():
            return config_path

    # Priority 3: Default location
    default_path = Path.home() / ".config" / "git" / "user-template"
    return default_path if default_path.exists() and default_path.is_dir() else None
