# git-workflow-utils

Shared utilities for git workflow automation scripts.

This package provides common git operations that can work either on the current working directory or on a specified repository path. Originally extracted from [wolf/dotfiles](https://github.com/wolf/dotfiles) git utilities.

## Features

- **Repository resolution**: Find and validate git repositories from relative or absolute paths
- **Branch discovery**: Intelligently find local and remote branches with wildcard support
- **Submodule management**: Automatically initialize and update submodules recursively
- **Direnv integration**: Create .envrc symlinks and run `direnv allow` if available
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
)

# Get current branch
branch = current_branch()
print(f"On branch: {branch}")

# Find branches matching a pattern
branches = find_branches("feature-*")
print(f"Feature branches: {branches}")

# Initialize a repository (submodules + direnv)
initialize_repo("/path/to/repo")

# Run git commands
result = run_git("status", "--short", capture=True)
print(result.stdout)
```

## API Reference

### Paths Module (`git_workflow_utils.paths`)

- **`resolve_path(path)`** - Resolve a path to an absolute Path object
- **`is_absolute_repo_path(repo)`** - Check if path is an absolute path to a git repository
- **`resolve_repo(repo)`** - Resolve and validate a git repository path

### Git Module (`git_workflow_utils.git`)

- **`run_git(*args, repo=None, check=True, capture=False)`** - Run a git command
- **`current_branch(repo=None)`** - Get the currently checked out branch name
- **`has_uncommitted_changes(repo=None)`** - Check for uncommitted changes
- **`fetch_all(repo=None, quiet=False)`** - Fetch all remotes, prune deleted refs, update tags
- **`find_branches(pattern, repo=None, remote_name="origin")`** - Find branches matching a pattern
- **`submodule_update(repo=None)`** - Update submodules recursively
- **`initialize_repo(repo=None)`** - Initialize a repository (submodules + direnv)

### Direnv Module (`git_workflow_utils.direnv`)

- **`is_direnv_available()`** - Check if direnv is installed
- **`direnv_allow(envrc)`** - Allow direnv to load a .envrc file
- **`setup_envrc(repo=None)`** - Create .envrc symlink from .envrc.sample and run direnv allow

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

The project has comprehensive test coverage (100%):

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/git_workflow_utils --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_git.py -v
```

**Test suite:**
- 50 tests total
- Unit tests for all modules
- Integration tests with real git repositories
- 100% code coverage

### Project Structure

```
git-workflow-utils/
├── src/git_workflow_utils/
│   ├── __init__.py       # Public API exports
│   ├── paths.py          # Path and repository resolution
│   ├── git.py            # Core git operations
│   ├── direnv.py         # Direnv integration
│   └── py.typed          # Type hint marker
├── tests/
│   ├── conftest.py       # Shared test fixtures
│   ├── test_paths.py     # Path module tests
│   ├── test_git.py       # Git module tests
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
