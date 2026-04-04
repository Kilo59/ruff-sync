"""Tests for the config_io module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ruff_sync.config_io import (
    is_ruff_toml_file,
    load_local_ruff_config,
    resolve_target_path,
)

if TYPE_CHECKING:
    import pathlib


def test_is_ruff_toml_file() -> None:
    assert is_ruff_toml_file("ruff.toml") is True
    assert is_ruff_toml_file(".ruff.toml") is True
    assert is_ruff_toml_file("pyproject.toml") is False
    assert is_ruff_toml_file("https://example.com/ruff.toml") is True
    assert is_ruff_toml_file("https://example.com/pyproject.toml") is False
    assert is_ruff_toml_file("ruff.toml?ref=main") is True
    assert is_ruff_toml_file("ruff.toml#L1-L10") is True


def test_resolve_target_path_existing_file(tmp_path: pathlib.Path) -> None:
    cfg = tmp_path / "custom.toml"
    cfg.touch()
    assert resolve_target_path(cfg) == cfg


def test_resolve_target_path_directory_discovery(tmp_path: pathlib.Path) -> None:
    # 1. Empty dir -> pyproject.toml (default)
    assert resolve_target_path(tmp_path) == tmp_path / "pyproject.toml"

    # 2. ruff.toml exists
    ruff_toml = tmp_path / "ruff.toml"
    ruff_toml.touch()
    assert resolve_target_path(tmp_path) == ruff_toml

    # 3. .ruff.toml exists (takes precedence over pyproject but not ruff.toml in our tried_order)
    ruff_toml.unlink()
    dot_ruff = tmp_path / ".ruff.toml"
    dot_ruff.touch()
    assert resolve_target_path(tmp_path) == dot_ruff


def test_load_local_ruff_config_pyproject(tmp_path: pathlib.Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff]
line-length = 120
[tool.ruff.lint]
select = ["E", "F"]
""",
        encoding="utf-8",
    )

    config = load_local_ruff_config(tmp_path)
    assert config == {"line-length": 120, "lint": {"select": ["E", "F"]}}
    assert isinstance(config, dict)


def test_load_local_ruff_config_pyproject_without_tool_ruff(tmp_path: pathlib.Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "example"

[tool.other]
value = 1
""",
        encoding="utf-8",
    )

    config = load_local_ruff_config(tmp_path)
    assert config == {}
    assert isinstance(config, dict)


def test_load_local_ruff_config_pyproject_tool_not_mapping(tmp_path: pathlib.Path) -> None:
    # Here "tool" exists but is not a mapping/table in the parsed TOML.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
tool = 1
""",
        encoding="utf-8",
    )

    config = load_local_ruff_config(tmp_path)
    assert config == {}
    assert isinstance(config, dict)


def test_load_local_ruff_config_pyproject_tool_ruff_not_mapping(tmp_path: pathlib.Path) -> None:
    # Here "tool" is a mapping, but "tool.ruff" is not a mapping/table.
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool]
ruff = 1
""",
        encoding="utf-8",
    )

    with pytest.raises(TypeError) as exc_info:
        load_local_ruff_config(tmp_path)

    # Ensure the error is specific to the tool.ruff section
    assert "tool.ruff" in str(exc_info.value)


def test_load_local_ruff_config_ruff_toml(tmp_path: pathlib.Path) -> None:
    ruff_toml = tmp_path / "ruff.toml"
    ruff_toml.write_text(
        """
line-length = 100
[lint]
ignore = ["D100"]
""",
        encoding="utf-8",
    )

    config = load_local_ruff_config(tmp_path)
    assert config == {"line-length": 100, "lint": {"ignore": ["D100"]}}


def test_load_local_ruff_config_ruff_toml_not_mapping(tmp_path: pathlib.Path) -> None:
    # An empty file is a valid TOML document but tomlkit might return an empty dict
    # or a document that unwraps to an empty dict.
    # To test the `isinstance(unwrapped, dict)` check for a non-dict,
    # we'd need a document that tomlkit parses but doesn't unwrap to a dict.
    # However, standard TOML always parses to a Table (dict-like).
    # We'll just verify that an empty ruff.toml returns an empty dict.
    ruff_toml = tmp_path / "ruff.toml"
    ruff_toml.write_text("", encoding="utf-8")

    config = load_local_ruff_config(tmp_path)
    assert config == {}
    assert isinstance(config, dict)


def test_load_local_ruff_config_missing(tmp_path: pathlib.Path) -> None:
    # resolve_target_path always returns a path, but it might not exist
    # load_local_ruff_config should raise FileNotFoundError if it doesn't exist
    with pytest.raises(FileNotFoundError):
        load_local_ruff_config(tmp_path / "nonexistent")
