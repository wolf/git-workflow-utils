# git-workflow-utils

Shared utilities for git workflow automation scripts.

This package provides common git operations that can work either on the current working directory or on a specified repository path. Originally extracted from [wolf/dotfiles](https://github.com/wolf/dotfiles) git utilities.

## Features

- **Repository resolution**: Find and validate git repositories from relative or absolute paths
- **Branch discovery**: Intelligently find local and remote branches with wildcard support
- **Submodule management**: Automatically initialize and update submodules recursively
- **Direnv integration**: Create .envrc symlinks and run `direnv allow` if available
- **User templates**: Automatically apply user-specific files to new worktrees and clones
- **Path utilities**: Handle tilde expansion and absolute path conversion
- **Git operations**: Run git commands with flexible options and error handling

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/wolf/git-workflow-utils.git

# Install from local directory (for development)
pip install -e /path/to/git-workflow-utils
```

For use with uv scripts, add to your inline metadata:

```python
# /// script
# dependencies = [
#     "git-workflow-utils @ git+https://github.com/wolf/git-workflow-utils.git",
# ]
# ///
```

## Usage

```python
from git_workflow_utils import (
    run_git,
    current_branch,
    find_branches,
    initialize_repo,
    resolve_repo,
    apply_user_template,
)

# Get current branch
branch = current_branch()
print(f"On branch: {branch}")

# Find branches matching a pattern
branches = find_branches("feature-*")
print(f"Feature branches: {branches}")

# Initialize a repository (submodules + direnv + user templates)
initialize_repo("/path/to/repo")

# Apply user templates to an existing repository
apply_user_template("/path/to/repo")

# Run git commands
result = run_git("status", "--short", capture=True)
print(result.stdout)
```

## User Templates

The user template system allows you to automatically populate new worktrees and clones with user-specific files that are typically gitignored (like `.envrc.local`, `.ipython/`, `.helix/`, etc.).

### Quick Start

1. **Create a template directory** with your user-specific files:

```bash
mkdir -p ~/.config/git/user-template
echo 'export MY_API_KEY=secret123' > ~/.config/git/user-template/.envrc.local
```

2. **Configure the template mode** (required):

```bash
# Use symlinks (changes propagate across all worktrees)
git config --global worktree.userTemplate.mode link

# Or use copies (each worktree gets independent copies)
git config --global worktree.userTemplate.mode copy
```

3. **Templates are applied automatically** when you use `initialize_repo()`:

```python
from git_workflow_utils import initialize_repo

# This will now apply user templates
initialize_repo("/path/to/new-worktree")
```

### Configuration

#### Template Location Priority

Templates are loaded from the first location that exists:

1. **Explicit path** (function parameter): `apply_user_template(repo, template_path=Path("~/my-template"))`
2. **Git config**: `git config worktree.userTemplate.path ~/.config/git/templates/python`
3. **Default location**: `~/.config/git/user-template/`

#### Template Mode (Required)

You **must** configure the mode if a template directory exists:

```bash
# Link mode: creates symlinks to template files
# Pro: Changes to template propagate to all repos
# Con: Can't customize per-repo
git config --global worktree.userTemplate.mode link

# Copy mode: copies template files
# Pro: Each repo can customize independently
# Con: Changes to template don't propagate
git config --global worktree.userTemplate.mode copy
```

#### Per-File Overrides

You can override the mode for specific files:

```bash
# Use link mode globally, but copy .ipython/ directory
git config --global worktree.userTemplate.mode link
git config --global --add worktree.userTemplate.copy .ipython

# Use copy mode globally, but link .envrc.local
git config --global worktree.userTemplate.mode copy
git config --global --add worktree.userTemplate.link .envrc.local
```

### Common Use Cases

#### Project-Specific IPython Configuration

```bash
# Template directory structure
~/.config/git/user-template/
└── .ipython/
    └── profile_default/
        └── startup/
            └── 00-imports.py  # Auto-import commonly used modules
```

#### Personal Environment Variables

```bash
# .envrc.local for secrets and personal config
~/.config/git/user-template/.envrc.local
```

Content:
```bash
# Personal API keys and tokens (gitignored)
export ANTHROPIC_API_KEY=sk-xxxxx
export GITHUB_TOKEN=ghp_xxxxx
```

#### Editor Configuration

```bash
# Helix editor project-specific settings
~/.config/git/user-template/.helix/
└── languages.toml
```

#### Multiple Template Sets

For different project types (Python, Rust, etc.):

```bash
# Create project-specific templates
~/.config/git/templates/
├── python/
│   ├── .envrc.local
│   └── .ipython/
└── rust/
    └── .envrc.local

# Use per-project config
cd ~/my-python-project
git config worktree.userTemplate.path ~/.config/git/templates/python
git config worktree.userTemplate.mode link
```

### Example: Complete Setup

```bash
# 1. Create template directory
mkdir -p ~/.config/git/user-template/.ipython/profile_default/startup

# 2. Add personal environment variables
cat > ~/.config/git/user-template/.envrc.local <<'EOF'
export ANTHROPIC_API_KEY=sk-xxxxx
export DATABASE_PASSWORD=hunter2
EOF

# 3. Add IPython auto-imports
cat > ~/.config/git/user-template/.ipython/profile_default/startup/00-imports.py <<'EOF'
# Auto-imported when IPython starts in project directory
from pathlib import Path
import sys
EOF

# 4. Configure template mode
git config --global worktree.userTemplate.mode link

# 5. Now all new clones/worktrees will get these files automatically!
```

## Configuration

All workflow configuration uses git config under the `workflow.*` namespace.
Set values with `git config` (local or global).

| Key | Default | Description |
|-----|---------|-------------|
| `workflow.ticket.prefix` | *(none)* | Prefix for bare ticket numbers (e.g., `SE`) |
| `workflow.ticket.urlPattern` | *(none)* | URL template with `%(ticket)` placeholder |
| `workflow.project.name` | *(computed)* | Project name override |
| `workflow.branch.localFormat` | `%(desc)` | Format string for local branch names |
| `workflow.branch.remoteFormat` | `%(type)/%(owner)/%(ticket)-%(desc)` | Format string for remote branch names |
| `workflow.branches.priority` | `prod,develop` | Comma-separated priority branch names |
| `workflow.branches.exclude` | `*archive/*` | Comma-separated glob patterns to exclude |

### Format string placeholders

Format strings use `%(name)` placeholders, expanded by `expand_format()`:

| Placeholder | Source |
|-------------|--------|
| `%(ticket)` | Ticket identifier (e.g., `SE-123`) |
| `%(desc)` | Branch description slug |
| `%(type)` | Branch type (`feature`, `bugfix`, `hotfix`) |
| `%(owner)` | Local part of `user.email` |

## API Reference

### Workflow Module (`git_workflow_utils.workflow`)

- **`get_workflow_config(key, repo=None, default=None)`** - Read a `workflow.*` git config value
- **`expand_format(format_string, **placeholders)`** - Expand `%(name)` placeholders in a format string
- **`get_owner(repo=None)`** - Get owner name from `user.email`
- **`get_project_name(repo=None)`** - Get project name (config > remote URL > directory name)
- **`get_local_branch_format(repo=None)`** - Get format string for local branch names
- **`get_remote_branch_format(repo=None)`** - Get format string for remote branch names
- **`get_priority_branches(repo=None)`** - Get branch names to show first in listings
- **`get_exclude_patterns(repo=None)`** - Get glob patterns to exclude from branch listings

### Description Module (`git_workflow_utils.description`)

- **`BranchDescription`** - Dataclass for structured branch descriptions (summary + trailers)
  - `get(key)` - Get first value for a trailer key (case-insensitive)
  - `get_all(key)` - Get all values for a trailer key
  - `replace(key, value)` - Set a single value (replacing any existing)
  - `add(key, value)` - Append a value (for multi-valued trailers like Ticket)
  - `tickets` / `remote` / `pr` - Convenience properties
- **`parse_branch_description(text)`** - Parse a description string into a `BranchDescription`
- **`format_branch_description(desc)`** - Format a `BranchDescription` back to a string
- **`build_branch_description(...)`** - Build a `BranchDescription` for a new branch

### Ticket Module (`git_workflow_utils.ticket`)

- **`normalize_ticket(ticket, repo=None)`** - Normalize a ticket identifier (expand bare numbers)
- **`get_ticket_url(ticket, repo=None)`** - Get a browsable URL for a ticket
- **`extract_ticket_from_branch(branch=None, repo=None, pattern=None)`** - Extract ticket from a branch name
- **`branch_matches_ticket(branch, ticket, check_details=True, repo=None)`** - Check if a branch matches a ticket
- **`find_matching_branches(ticket, ...)`** - Find branches associated with a ticket
- **`get_branch_commit_message(branch, repo=None)`** - Get the first commit message unique to a branch

### Paths Module (`git_workflow_utils.paths`)

- **`resolve_path(path)`** - Resolve a path to an absolute Path object
- **`is_absolute_repo_path(repo)`** - Check if path is an absolute path to a git repository
- **`resolve_repo(repo)`** - Resolve and validate a git repository path

### Git Module (`git_workflow_utils.git`)

- **`run_git(*args, repo=None, check=True, capture=False)`** - Run a git command
- **`git_config(key, repo=None, default=None)`** - Get a git config value
- **`git_config_list(key, repo=None)`** - Get all values for a multi-value git config key
- **`current_branch(repo=None)`** - Get the currently checked out branch name
- **`has_uncommitted_changes(repo=None)`** - Check for uncommitted changes
- **`fetch_all(repo=None, quiet=False)`** - Fetch all remotes, prune deleted refs, update tags
- **`find_branches(pattern, repo=None, remote_name="origin")`** - Find branches matching a pattern
- **`submodule_update(repo=None)`** - Update submodules recursively
- **`initialize_repo(repo=None)`** - Initialize a repository (submodules + direnv + user templates)

### Templates Module (`git_workflow_utils.templates`)

- **`symlink_envrc_if_needed(repo=None, template=".envrc.sample")`** - Create .envrc symlink from template file
- **`apply_user_template(repo=None, template_path=None)`** - Apply user template directory to repository

### Direnv Module (`git_workflow_utils.direnv`)

- **`is_direnv_available()`** - Check if direnv is installed
- **`direnv_allow(envrc)`** - Allow direnv to load a .envrc file

## Development

### Setup

```bash
# Clone the repository
git clone github:wolf/git-workflow-utils.git
cd git-workflow-utils

# Activate direnv (sets up uv environment and IPython)
direnv allow

# Or manually install dependencies
uv sync --all-extras
```

### Testing

The project has comprehensive test coverage (96%):

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/git_workflow_utils --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_git.py -v
```

**Test suite:**
- 85 tests total
- Unit tests for all modules
- Integration tests with real git repositories
- 96% code coverage (100% on new templates module)

### Project Structure

```
git-workflow-utils/
├── src/git_workflow_utils/
│   ├── __init__.py       # Public API exports
│   ├── paths.py          # Path and repository resolution
│   ├── git.py            # Core git operations
│   ├── workflow.py       # Workflow config and format strings
│   ├── description.py    # Branch description parsing (git trailers)
│   ├── ticket.py         # Ticket extraction and matching
│   ├── templates.py      # User template system
│   ├── direnv.py         # Direnv integration
│   └── py.typed          # Type hint marker
├── tests/
│   ├── conftest.py       # Shared test fixtures
│   ├── test_paths.py     # Path module tests
│   ├── test_git.py       # Git module tests
│   ├── test_workflow.py  # Workflow module tests
│   ├── test_description.py # Description module tests
│   ├── test_ticket.py    # Ticket module tests
│   ├── test_templates.py # Template module tests
│   └── test_direnv.py    # Direnv module tests
├── .ipython/             # Local IPython configuration
├── .envrc                # Direnv configuration (uv + IPython)
├── pyproject.toml        # Package configuration
└── README.md             # This file
```

## Requirements

- Python 3.13+
- Git 2.0+
- direnv (optional, for .envrc support)

## License

Part of Wolf's personal utilities. Use at your own discretion.

## Contributing

This is a personal utilities repository, but suggestions and improvements are welcome via issues or pull requests.
