"""Performance benchmarks for ruff-sync core operations."""

from __future__ import annotations

import subprocess
import sys

import pytest
import tomlkit
from httpx import URL
from pytest_codspeed import BenchmarkFixture
from tomlkit import TOMLDocument
from tomlkit.items import Table

from ruff_sync.core import (
    _find_changed_keys,
    _recursive_update,
    get_ruff_config,
    merge_ruff_toml,
    resolve_raw_url,
)

pytestmark = pytest.mark.benchmark

# ---------------------------------------------------------------------------
# Fixtures: realistic TOML documents used across benchmarks
# ---------------------------------------------------------------------------

SMALL_PYPROJECT = """\
[project]
name = "my-project"
version = "1.0.0"
requires-python = ">=3.10"

[tool.ruff]
target-version = "py310"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W"]
ignore = ["E501"]
"""

LARGE_PYPROJECT = """\
[project]
name = "large-project"
version = "2.0.0"
requires-python = ">=3.10"

[tool.ruff]
target-version = "py310"
line-length = 100

[tool.ruff.lint]
select = [
    "ASYNC",
    "B",
    "C",
    "D",
    "DTZ",
    "EM",
    "F",
    "E",
    "W",
    "G",
    "I",
    "ICN",
    "N",
    "LOG",
    "PERF",
    "PGH",
    "PTH",
    "PL",
    "FA",
    "FURB",
    "RUF",
    "S",
    "SIM",
    "SLOT",
    "TC",
    "TID",
    "TRY",
    "T20",
    "UP",
]
ignore = ["G004", "TRY003"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["T20", "D100", "D101", "D103", "S101", "PLR2004"]
"scripts/**/*.py" = ["T20", "ASYNC"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.pylint]
max-args = 6

[tool.ruff.format]
docstring-code-format = true
docstring-code-line-length = "dynamic"

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"unittest.mock".msg = "Use dedicated mocking libraries."

[tool.ruff.lint.flake8-import-conventions]
banned-from = ["pathlib", "datetime"]

[tool.ruff.lint.flake8-import-conventions.aliases]
datetime = "dt"

[tool.ruff.lint.isort]
required-imports = ["from __future__ import annotations"]
"""

UPSTREAM_RUFF_SECTION = """\
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = [
    "ASYNC",
    "B",
    "C",
    "D",
    "DTZ",
    "EM",
    "F",
    "E",
    "W",
    "G",
    "I",
    "ICN",
    "N",
    "LOG",
    "PERF",
    "PGH",
    "PTH",
    "PL",
    "FA",
    "FURB",
    "RUF",
    "S",
    "SIM",
    "SLOT",
    "TC",
    "TID",
    "TRY",
    "T20",
    "UP",
    "FBT",
]
ignore = ["G004", "TRY003", "D107"]

[tool.ruff.lint.pydocstyle]
convention = "numpy"

[tool.ruff.lint.pylint]
max-args = 8

[tool.ruff.format]
docstring-code-format = true
docstring-code-line-length = 80
"""


# ---------------------------------------------------------------------------
# Benchmarks: URL resolution
# ---------------------------------------------------------------------------


def test_bench_resolve_raw_url_github_repo(benchmark: BenchmarkFixture):
    """Benchmark resolving a GitHub repository URL to raw content."""
    url = URL("https://github.com/Kilo59/ruff-sync")
    benchmark(resolve_raw_url, url, branch="main", path=None)


def test_bench_resolve_raw_url_github_blob(benchmark: BenchmarkFixture):
    """Benchmark resolving a GitHub blob URL."""
    url = URL("https://github.com/Kilo59/ruff-sync/blob/main/pyproject.toml")
    benchmark(resolve_raw_url, url, branch="main", path=None)


def test_bench_resolve_raw_url_github_tree(benchmark: BenchmarkFixture):
    """Benchmark resolving a GitHub tree URL."""
    url = URL("https://github.com/Kilo59/ruff-sync/tree/main/configs/kitchen-sink")
    benchmark(resolve_raw_url, url, branch="main", path=None)


def test_bench_resolve_raw_url_gitlab(benchmark: BenchmarkFixture):
    """Benchmark resolving a GitLab URL."""
    url = URL("https://gitlab.com/my-org/my-repo")
    benchmark(resolve_raw_url, url, branch="main", path=None)


# ---------------------------------------------------------------------------
# Benchmarks: TOML parsing and config extraction
# ---------------------------------------------------------------------------


def test_bench_get_ruff_config_small(benchmark: BenchmarkFixture):
    """Benchmark extracting ruff config from a small pyproject.toml."""
    benchmark(get_ruff_config, SMALL_PYPROJECT, is_ruff_toml=False, exclude=())


def test_bench_get_ruff_config_large(benchmark: BenchmarkFixture):
    """Benchmark extracting ruff config from a large pyproject.toml."""
    benchmark(get_ruff_config, LARGE_PYPROJECT, is_ruff_toml=False, exclude=())


def test_bench_get_ruff_config_with_exclusions(benchmark: BenchmarkFixture):
    """Benchmark extracting ruff config with multiple exclusions."""
    exclusions = [
        "target-version",
        "lint.per-file-ignores",
        "lint.ignore",
        "lint.flake8-tidy-imports.banned-api",
        "lint.isort.required-imports",
    ]
    benchmark(get_ruff_config, LARGE_PYPROJECT, is_ruff_toml=False, exclude=exclusions)


# ---------------------------------------------------------------------------
# Benchmarks: TOML merging
# ---------------------------------------------------------------------------


def test_bench_merge_ruff_toml_small(benchmark: BenchmarkFixture):
    """Benchmark merging a small config with upstream changes."""
    source = tomlkit.parse(SMALL_PYPROJECT)
    upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
    benchmark(merge_ruff_toml, source, upstream_ruff)


def test_bench_merge_ruff_toml_large(benchmark: BenchmarkFixture):
    """Benchmark merging a large config with upstream changes."""
    source = tomlkit.parse(LARGE_PYPROJECT)
    upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
    benchmark(merge_ruff_toml, source, upstream_ruff)


def test_bench_merge_with_exclusions(benchmark: BenchmarkFixture):
    """Benchmark merging with exclusions applied."""
    exclusions = ["target-version", "lint.per-file-ignores", "lint.ignore"]
    source = tomlkit.parse(LARGE_PYPROJECT)
    upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=exclusions)
    benchmark(merge_ruff_toml, source, upstream_ruff)


# ---------------------------------------------------------------------------
# Benchmarks: recursive update (core merge primitive)
# ---------------------------------------------------------------------------


def test_bench_recursive_update(benchmark: BenchmarkFixture):
    """Benchmark the recursive update of nested TOML tables."""
    source = tomlkit.parse(LARGE_PYPROJECT)
    upstream = tomlkit.parse(UPSTREAM_RUFF_SECTION)

    source_tool = source["tool"]
    upstream_tool = upstream["tool"]
    assert isinstance(source_tool, Table)
    assert isinstance(upstream_tool, Table)

    source_ruff = source_tool["ruff"]
    upstream_ruff = upstream_tool["ruff"]

    benchmark(_recursive_update, source_ruff, upstream_ruff)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Benchmarks: diff / changed key detection
# ---------------------------------------------------------------------------


def test_bench_find_changed_keys_no_changes(benchmark: BenchmarkFixture):
    """Benchmark finding changed keys when configs are identical."""
    doc = tomlkit.parse(LARGE_PYPROJECT)
    tool = doc["tool"]
    assert isinstance(tool, Table)
    ruff_section = tool["ruff"]
    unwrapped = ruff_section.unwrap()
    benchmark(_find_changed_keys, unwrapped, unwrapped)


def test_bench_find_changed_keys_with_changes(benchmark: BenchmarkFixture):
    """Benchmark finding changed keys between differing configs."""
    source_doc = tomlkit.parse(LARGE_PYPROJECT)
    merged_doc = tomlkit.parse(LARGE_PYPROJECT)

    # Apply upstream changes to create differences
    upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
    merge_ruff_toml(merged_doc, upstream_ruff)

    source_tool = source_doc["tool"]
    merged_tool = merged_doc["tool"]
    assert isinstance(source_tool, Table)
    assert isinstance(merged_tool, Table)

    source_section = source_tool["ruff"].unwrap()
    merged_section = merged_tool["ruff"].unwrap()

    benchmark(_find_changed_keys, source_section, merged_section)


# ---------------------------------------------------------------------------
# Benchmarks: full TOML parse roundtrip
# ---------------------------------------------------------------------------


def test_bench_toml_parse_and_serialize(benchmark: BenchmarkFixture):
    """Benchmark parsing and re-serializing a large TOML document."""

    def roundtrip():
        doc: TOMLDocument = tomlkit.parse(LARGE_PYPROJECT)
        return doc.as_string()

    benchmark(roundtrip)


def test_cli_help_responsiveness(benchmark: BenchmarkFixture) -> None:
    """
    Measures the instruction count/performance of the --help command via subprocess.
    Using a subprocess ensures a clean environment and avoids polluting sys.modules.
    """

    def run_cli() -> None:
        subprocess.run(
            [sys.executable, "-m", "ruff_sync", "--help"],
            capture_output=True,
            check=True,
        )

    benchmark(run_cli)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
