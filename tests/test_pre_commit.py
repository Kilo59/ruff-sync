"""Tests for pre-commit sync module."""

from __future__ import annotations

import pathlib

import pytest

from ruff_sync.pre_commit import resolve_ruff_version, sync_pre_commit


@pytest.fixture
def base_dir(fs) -> pathlib.Path:
    """Return a mock base directory."""
    path = pathlib.Path("/mock_project")
    fs.create_dir(path)
    return path


def test_resolve_ruff_version_uv_lock(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(
        base_dir / "uv.lock",
        contents="""
[[package]]
name = "ruff"
version = "0.15.2"
""",
    )
    assert resolve_ruff_version(base_dir) == "0.15.2"


def test_resolve_ruff_version_empty_uv_lock_pyproject_fallback(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / "uv.lock", contents="")
    fs.create_file(
        base_dir / "pyproject.toml",
        contents="""
[dependency-groups]
dev = ["ruff>=0.14.0", "pytest"]
""",
    )
    assert resolve_ruff_version(base_dir) == "0.14.0"


def test_resolve_ruff_version_pyproject_project_deps(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(
        base_dir / "pyproject.toml",
        contents="""
[project]
dependencies = ["ruff==0.13.1", "httpx"]
""",
    )
    assert resolve_ruff_version(base_dir) == "0.13.1"


def test_resolve_ruff_version_none(fs, base_dir: pathlib.Path) -> None:
    assert resolve_ruff_version(base_dir) is None


def test_sync_pre_commit_no_config(fs, base_dir: pathlib.Path) -> None:
    # No config file exists
    assert sync_pre_commit(base_dir) is True


def test_sync_pre_commit_no_version(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / ".pre-commit-config.yaml", contents="")
    assert sync_pre_commit(base_dir) is True


def test_sync_pre_commit_already_in_sync(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / "uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.0
    hooks:
      - id: ruff
"""
    fs.create_file(base_dir / ".pre-commit-config.yaml", contents=config_content)
    assert sync_pre_commit(base_dir) is True
    assert (base_dir / ".pre-commit-config.yaml").read_text() == config_content


def test_sync_pre_commit_out_of_sync_dry_run(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / "uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.0
    hooks:
      - id: ruff
"""
    fs.create_file(base_dir / ".pre-commit-config.yaml", contents=config_content)
    assert sync_pre_commit(base_dir, dry_run=True) is False
    assert (base_dir / ".pre-commit-config.yaml").read_text() == config_content


def test_sync_pre_commit_out_of_sync_update(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / "uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: 'v0.14.0'
"""
    fs.create_file(base_dir / ".pre-commit-config.yaml", contents=config_content)
    assert sync_pre_commit(base_dir, dry_run=False) is True
    updated_content = (base_dir / ".pre-commit-config.yaml").read_text()
    assert "rev: 'v0.15.0'" in updated_content


def test_sync_pre_commit_out_of_sync_update_no_v(fs, base_dir: pathlib.Path) -> None:
    fs.create_file(base_dir / "uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    # Testing stripping of 'v'
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: "0.14.0"
    """
    fs.create_file(base_dir / ".pre-commit-config.yaml", contents=config_content)
    assert sync_pre_commit(base_dir, dry_run=False) is True
    updated_content = (base_dir / ".pre-commit-config.yaml").read_text()
    assert 'rev: "0.15.0"' in updated_content
