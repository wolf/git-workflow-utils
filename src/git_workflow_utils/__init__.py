"""Shared utilities for git workflow automation scripts.

This package provides common git operations that can work either on the current
working directory or on a specified repository path.
"""

# Re-export all public functions from submodules
from .direnv import (
    direnv_allow,
    is_direnv_available,
    setup_envrc,
)
from .git import (
    current_branch,
    fetch_all,
    find_branches,
    find_git_repos,
    get_commits,
    has_uncommitted_changes,
    initialize_repo,
    run_git,
    submodule_update,
    user_email_in_this_working_copy,
)
from .paths import (
    is_absolute_repo_path,
    resolve_path,
    resolve_repo,
)

__all__ = (
    "current_branch",
    "direnv_allow",
    "fetch_all",
    "find_branches",
    "find_git_repos",
    "get_commits",
    "has_uncommitted_changes",
    "initialize_repo",
    "is_absolute_repo_path",
    "is_direnv_available",
    "resolve_path",
    "resolve_repo",
    "run_git",
    "setup_envrc",
    "submodule_update",
    "user_email_in_this_working_copy",
)
