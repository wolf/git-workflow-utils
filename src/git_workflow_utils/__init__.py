"""Shared utilities for git workflow automation scripts.

This package provides common git operations that can work either on the current
working directory or on a specified repository path.
"""

# Re-export all public functions from submodules
from .direnv import (
    direnv_allow,
    is_direnv_available,
)
from .git import (
    current_branch,
    fetch_all,
    filter_repos_by_ignore_file,
    find_branches,
    find_git_repos,
    get_commits,
    git_config,
    git_config_list,
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
    sanitize_directory_name,
)
from .templates import (
    apply_user_template,
    symlink_envrc_if_needed,
)

__all__ = (
    "apply_user_template",
    "current_branch",
    "direnv_allow",
    "fetch_all",
    "filter_repos_by_ignore_file",
    "find_branches",
    "find_git_repos",
    "get_commits",
    "git_config",
    "git_config_list",
    "has_uncommitted_changes",
    "initialize_repo",
    "is_absolute_repo_path",
    "is_direnv_available",
    "resolve_path",
    "resolve_repo",
    "run_git",
    "sanitize_directory_name",
    "submodule_update",
    "symlink_envrc_if_needed",
    "user_email_in_this_working_copy",
)
