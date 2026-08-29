from __future__ import annotations

import pathlib

import pytest
import tomlkit

from ruff_sync.validation import validate_ruff_accepts_config

CONFIGS_DIR = pathlib.Path("configs")
CONFIG_NAMES = ["kitchen-sink", "fastapi", "data-science-engineering"]


@pytest.mark.parametrize("config_name", CONFIG_NAMES)
def test_predefined_configs_exist_and_valid_toml(config_name: str) -> None:
    """Ensure every predefined configuration exists and is valid TOML."""
    config_path = CONFIGS_DIR / config_name / "ruff.toml"
    assert config_path.is_file(), f"Expected config file not found: {config_path}"

    content = config_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)
    assert isinstance(doc, tomlkit.TOMLDocument)


@pytest.mark.parametrize("config_name", CONFIG_NAMES)
def test_predefined_configs_accepted_by_ruff_strict(config_name: str) -> None:
    """Ensure Ruff validates every predefined configuration without errors or warnings."""
    config_path = CONFIGS_DIR / config_name / "ruff.toml"
    content = config_path.read_text(encoding="utf-8")
    doc = tomlkit.parse(content)

    is_valid = validate_ruff_accepts_config(doc, is_ruff_toml=True, strict=True)
    assert is_valid is True, f"Ruff rejected configuration {config_path}"


@pytest.mark.parametrize("config_name", CONFIG_NAMES)
def test_predefined_configs_core_structure(config_name: str) -> None:
    """Ensure predefined configurations follow standardized core settings."""
    config_path = CONFIGS_DIR / config_name / "ruff.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))

    raw = doc.unwrap()
    assert raw.get("line-length") == 88
    assert raw.get("indent-width") == 4
    assert raw.get("target-version") == "py310"

    assert "lint" in raw
    lint = raw["lint"]
    assert isinstance(lint.get("select"), list)
    assert len(lint["select"]) > 0

    assert "format" in raw
    fmt = raw["format"]
    assert fmt.get("quote-style") == "double"
    assert fmt.get("indent-style") == "space"
    assert fmt.get("docstring-code-format") is True
    assert fmt.get("docstring-code-line-length") == "dynamic"
    assert fmt.get("nested-string-quote-style") == "alternating"


def test_fastapi_config_specifics() -> None:
    """Ensure FastAPI configuration has web and Pydantic rules configured."""
    config_path = CONFIGS_DIR / "fastapi" / "ruff.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    raw = doc.unwrap()

    select = raw["lint"]["select"]
    assert "FAST" in select
    assert "ASYNC" in select
    assert "LOG" in select
    assert "RUF" in select

    assert raw["lint"]["pydocstyle"]["convention"] == "google"

    decorators = raw["lint"]["pep8-naming"]["classmethod-decorators"]
    assert "pydantic.field_validator" in decorators
    assert "pydantic.model_validator" in decorators


def test_data_science_config_specifics() -> None:
    """Ensure Data Science & Engineering config has NumPy, Pandas, and notebook settings."""
    config_path = CONFIGS_DIR / "data-science-engineering" / "ruff.toml"
    doc = tomlkit.parse(config_path.read_text(encoding="utf-8"))
    raw = doc.unwrap()

    assert "*.ipynb" in raw.get("extend-include", [])

    select = raw["lint"]["select"]
    assert "NPY" in select
    assert "PD" in select
    assert "AIR" in select
    assert "PERF" in select
    assert "LOG" in select
    assert "RUF" in select

    assert raw["lint"]["pydocstyle"]["convention"] == "numpy"

    per_file = raw["lint"]["per-file-ignores"]
    assert "*.ipynb" in per_file
    assert "E402" in per_file["*.ipynb"]
    assert "T201" in per_file["*.ipynb"]
