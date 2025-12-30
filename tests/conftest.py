"""Shared pytest fixtures for git-workflow-utils tests."""

import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def git_repo(tmp_path):
    """
    Create a temporary git repository for testing.

    Returns:
        Path: Path to the temporary git repository
    """
    repo = tmp_path / "test-repo"
    repo.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    return repo


@pytest.fixture
def git_repo_with_remote(tmp_path, git_repo):
    """
    Create a git repository with a remote (bare repo).

    Returns:
        tuple: (main_repo_path, remote_repo_path)
    """
    remote_repo = tmp_path / "remote"
    remote_repo.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=remote_repo, check=True, capture_output=True)

    # Add remote and push main
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote_repo)],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    return git_repo, remote_repo
