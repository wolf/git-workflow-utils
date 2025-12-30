"""Tests for direnv module."""

import os
import subprocess
from pathlib import Path

import pytest

from git_workflow_utils.direnv import direnv_allow, is_direnv_available, setup_envrc


class TestIsDirenvAvailable:
    """Tests for is_direnv_available function."""

    def test_returns_bool(self):
        result = is_direnv_available()
        assert isinstance(result, bool)

    def test_false_when_not_in_path(self, monkeypatch):
        monkeypatch.setenv("PATH", "")
        assert is_direnv_available() is False

    def test_true_when_in_path(self, monkeypatch, tmp_path):
        # Create a fake direnv executable
        fake_direnv = tmp_path / "direnv"
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path))
        assert is_direnv_available() is True


class TestDirenvAllow:
    """Tests for direnv_allow function."""

    def test_does_nothing_when_direnv_not_available(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PATH", "")
        envrc = tmp_path / ".envrc"
        envrc.write_text("export TEST=1")
        direnv_allow(envrc)  # Should not raise

    def test_does_nothing_for_non_envrc_file(self, tmp_path, monkeypatch):
        # Even with direnv available, wrong filename should be ignored
        fake_direnv = tmp_path / "bin" / "direnv"
        fake_direnv.parent.mkdir()
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path / "bin"))

        other_file = tmp_path / "notenvrc"
        other_file.write_text("export TEST=1")
        direnv_allow(other_file)  # Should not raise

    def test_does_nothing_for_nonexistent_file(self, tmp_path, monkeypatch):
        fake_direnv = tmp_path / "bin" / "direnv"
        fake_direnv.parent.mkdir()
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(tmp_path / "bin"))

        envrc = tmp_path / ".envrc"
        direnv_allow(envrc)  # Should not raise

    def test_runs_direnv_allow_when_conditions_met(self, tmp_path, monkeypatch):
        # Create a fake direnv that records it was called
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_direnv = bin_dir / "direnv"
        marker = tmp_path / "direnv-was-called"
        fake_direnv.write_text(f"#!/bin/sh\n/usr/bin/touch {marker}\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

        envrc_dir = tmp_path / "project"
        envrc_dir.mkdir()
        envrc = envrc_dir / ".envrc"
        envrc.write_text("export TEST=1")

        direnv_allow(envrc)

        assert marker.exists(), "direnv allow should have been called"


class TestSetupEnvrc:
    """Tests for setup_envrc function."""

    def test_does_nothing_when_direnv_not_available(self, git_repo, monkeypatch):
        monkeypatch.setenv("PATH", "")
        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export TEST=1")
        setup_envrc(git_repo)
        envrc = git_repo / ".envrc"
        assert not envrc.exists()

    def test_creates_symlink_when_sample_exists(self, git_repo, monkeypatch, tmp_path):
        # Create fake direnv
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_direnv = bin_dir / "direnv"
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export TEST=1")

        setup_envrc(git_repo)

        envrc = git_repo / ".envrc"
        assert envrc.exists()
        assert envrc.is_symlink()
        assert envrc.resolve() == envrc_sample.resolve()

    def test_does_not_overwrite_existing_envrc(self, git_repo, monkeypatch, tmp_path):
        # Create fake direnv
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_direnv = bin_dir / "direnv"
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

        envrc_sample = git_repo / ".envrc.sample"
        envrc_sample.write_text("export TEST=1")

        envrc = git_repo / ".envrc"
        envrc.write_text("export EXISTING=1")
        original_content = envrc.read_text()

        setup_envrc(git_repo)

        # Should not have changed
        assert envrc.read_text() == original_content
        assert not envrc.is_symlink()

    def test_runs_direnv_allow_on_existing_envrc(self, git_repo, monkeypatch, tmp_path):
        # Create fake direnv that records being called
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        marker = tmp_path / "direnv-called"
        fake_direnv = bin_dir / "direnv"
        fake_direnv.write_text(f"#!/bin/sh\n/usr/bin/touch {marker}\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

        envrc = git_repo / ".envrc"
        envrc.write_text("export TEST=1")

        setup_envrc(git_repo)

        assert marker.exists(), "direnv allow should have been called"

    def test_does_nothing_when_no_envrc_or_sample(self, git_repo, monkeypatch, tmp_path):
        # Create fake direnv
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()
        fake_direnv = bin_dir / "direnv"
        fake_direnv.write_text("#!/bin/sh\nexit 0")
        fake_direnv.chmod(0o755)
        monkeypatch.setenv("PATH", str(bin_dir))

        setup_envrc(git_repo)

        envrc = git_repo / ".envrc"
        assert not envrc.exists()
