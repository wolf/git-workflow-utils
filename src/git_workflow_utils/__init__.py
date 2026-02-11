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
    enable_worktree_config,
    fetch_all,
    filter_repos_by_ignore_file,
    find_branches,
    find_git_repos,
    get_branch_description,
    get_branch_upstream,
    get_branches_with_descriptions,
    get_commits,
    get_git_common_dir,
    get_local_branches,
    get_remote_branches,
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
from .ticket import (
    branch_matches_ticket,
    extract_ticket_from_branch,
    find_matching_branches,
    get_branch_commit_message,
    get_ticket_url,
    normalize_ticket,
)
from .workflow import (
    expand_format,
    get_exclude_patterns,
    get_local_branch_format,
    get_owner,
    get_priority_branches,
    get_project_name,
    get_remote_branch_format,
    get_workflow_config,
)

__all__ = (
    "apply_user_template",
    "branch_matches_ticket",
    "current_branch",
    "direnv_allow",
    "enable_worktree_config",
    "expand_format",
    "extract_ticket_from_branch",
    "fetch_all",
    "filter_repos_by_ignore_file",
    "find_branches",
    "find_git_repos",
    "find_matching_branches",
    "get_branch_commit_message",
    "get_branch_description",
    "get_branch_upstream",
    "get_branches_with_descriptions",
    "get_commits",
    "get_exclude_patterns",
    "get_git_common_dir",
    "get_local_branch_format",
    "get_local_branches",
    "get_owner",
    "get_priority_branches",
    "get_project_name",
    "get_remote_branch_format",
    "get_remote_branches",
    "get_ticket_url",
    "get_workflow_config",
    "git_config",
    "git_config_list",
    "has_uncommitted_changes",
    "initialize_repo",
    "is_absolute_repo_path",
    "is_direnv_available",
    "normalize_ticket",
    "resolve_path",
    "resolve_repo",
    "run_git",
    "sanitize_directory_name",
    "submodule_update",
    "symlink_envrc_if_needed",
    "user_email_in_this_working_copy",
)
