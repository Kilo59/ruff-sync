"""Performance benchmarks for ruff-sync core operations."""

from __future__ import annotations

import pytest
import tomlkit
from httpx import URL
from tomlkit import TOMLDocument

from ruff_sync.core import (
    _find_changed_keys,
    _recursive_update,
    get_ruff_config,
    merge_ruff_toml,
    resolve_raw_url,
)

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


@pytest.mark.benchmark
def test_bench_resolve_raw_url_github_repo(benchmark):
    """Benchmark resolving a GitHub repository URL to raw content."""
    url = URL("https://github.com/Kilo59/ruff-sync")
    benchmark(resolve_raw_url, url, branch="main", path=None)


@pytest.mark.benchmark
def test_bench_resolve_raw_url_github_blob(benchmark):
    """Benchmark resolving a GitHub blob URL."""
    url = URL("https://github.com/Kilo59/ruff-sync/blob/main/pyproject.toml")
    benchmark(resolve_raw_url, url, branch="main", path=None)


@pytest.mark.benchmark
def test_bench_resolve_raw_url_github_tree(benchmark):
    """Benchmark resolving a GitHub tree URL."""
    url = URL("https://github.com/Kilo59/ruff-sync/tree/main/configs/kitchen-sink")
    benchmark(resolve_raw_url, url, branch="main", path=None)


@pytest.mark.benchmark
def test_bench_resolve_raw_url_gitlab(benchmark):
    """Benchmark resolving a GitLab URL."""
    url = URL("https://gitlab.com/my-org/my-repo")
    benchmark(resolve_raw_url, url, branch="main", path=None)


# ---------------------------------------------------------------------------
# Benchmarks: TOML parsing and config extraction
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_bench_get_ruff_config_small(benchmark):
    """Benchmark extracting ruff config from a small pyproject.toml."""
    benchmark(get_ruff_config, SMALL_PYPROJECT, is_ruff_toml=False, exclude=())


@pytest.mark.benchmark
def test_bench_get_ruff_config_large(benchmark):
    """Benchmark extracting ruff config from a large pyproject.toml."""
    benchmark(get_ruff_config, LARGE_PYPROJECT, is_ruff_toml=False, exclude=())


@pytest.mark.benchmark
def test_bench_get_ruff_config_with_exclusions(benchmark):
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


@pytest.mark.benchmark
def test_bench_merge_ruff_toml_small(benchmark):
    """Benchmark merging a small config with upstream changes."""

    def do_merge():
        source = tomlkit.parse(SMALL_PYPROJECT)
        upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
        return merge_ruff_toml(source, upstream_ruff)

    benchmark(do_merge)


@pytest.mark.benchmark
def test_bench_merge_ruff_toml_large(benchmark):
    """Benchmark merging a large config with upstream changes."""

    def do_merge():
        source = tomlkit.parse(LARGE_PYPROJECT)
        upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
        return merge_ruff_toml(source, upstream_ruff)

    benchmark(do_merge)


@pytest.mark.benchmark
def test_bench_merge_with_exclusions(benchmark):
    """Benchmark merging with exclusions applied."""
    exclusions = ["target-version", "lint.per-file-ignores", "lint.ignore"]

    def do_merge():
        source = tomlkit.parse(LARGE_PYPROJECT)
        upstream_ruff = get_ruff_config(
            UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=exclusions
        )
        return merge_ruff_toml(source, upstream_ruff)

    benchmark(do_merge)


# ---------------------------------------------------------------------------
# Benchmarks: recursive update (core merge primitive)
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_bench_recursive_update(benchmark):
    """Benchmark the recursive update of nested TOML tables."""

    def do_update():
        source = tomlkit.parse(LARGE_PYPROJECT)
        upstream = tomlkit.parse(UPSTREAM_RUFF_SECTION)
        source_ruff = source["tool"]["ruff"]
        upstream_ruff = upstream["tool"]["ruff"]
        _recursive_update(source_ruff, upstream_ruff)

    benchmark(do_update)


# ---------------------------------------------------------------------------
# Benchmarks: diff / changed key detection
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_bench_find_changed_keys_no_changes(benchmark):
    """Benchmark finding changed keys when configs are identical."""
    doc = tomlkit.parse(LARGE_PYPROJECT)
    ruff_section = doc["tool"]["ruff"]
    unwrapped = ruff_section.unwrap()
    benchmark(_find_changed_keys, unwrapped, unwrapped)


@pytest.mark.benchmark
def test_bench_find_changed_keys_with_changes(benchmark):
    """Benchmark finding changed keys between differing configs."""
    source_doc = tomlkit.parse(LARGE_PYPROJECT)
    merged_doc = tomlkit.parse(LARGE_PYPROJECT)

    # Apply upstream changes to create differences
    upstream_ruff = get_ruff_config(UPSTREAM_RUFF_SECTION, is_ruff_toml=False, exclude=())
    merge_ruff_toml(merged_doc, upstream_ruff)

    source_section = source_doc["tool"]["ruff"].unwrap()
    merged_section = merged_doc["tool"]["ruff"].unwrap()

    benchmark(_find_changed_keys, source_section, merged_section)


# ---------------------------------------------------------------------------
# Benchmarks: full TOML parse roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_bench_toml_parse_and_serialize(benchmark):
    """Benchmark parsing and re-serializing a large TOML document."""

    def roundtrip():
        doc: TOMLDocument = tomlkit.parse(LARGE_PYPROJECT)
        return doc.as_string()

    benchmark(roundtrip)
