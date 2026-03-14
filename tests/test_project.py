from __future__ import annotations

import logging
import pathlib
import sys
from pprint import pformat as pf
from typing import TYPE_CHECKING, Any, Final, cast

import pytest
import tomlkit
from packaging.version import Version
from ruamel.yaml import YAML

import ruff_sync

if TYPE_CHECKING:
    from collections.abc import Mapping

yaml = YAML(typ="safe")

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

PROJECT_ROOT: Final = pathlib.Path(__file__).parent.parent
PYPROJECT_TOML: Final = PROJECT_ROOT / "pyproject.toml"

PYTHON_VERSION: Final = Version(sys.version.split()[0])
# TODO: get this from pyproject.toml
MIN_PYTHON_VERSION: Final = Version("3.10")


@pytest.fixture
def pre_commit_config_repos() -> Mapping[str, dict]:
    """
    Extract the repos from the pre-commit config file and return a dict with the
    repo source url as the key
    """
    pre_commit_config = PROJECT_ROOT / ".pre-commit-config.yaml"
    yaml_dict = yaml.load(pre_commit_config.read_bytes())
    LOGGER.info(f".pre-commit-config.yaml ->\n {pf(yaml_dict, depth=1)}")
    return {repo.pop("repo"): repo for repo in yaml_dict["repos"]}


@pytest.fixture
def uv_lock_packages() -> Mapping[str, dict]:
    uv_lock = PROJECT_ROOT / "uv.lock"
    toml_doc = tomlkit.loads(uv_lock.read_text())
    LOGGER.info(f"uv.lock ->\n {pf(toml_doc, depth=1)[:1000]}...")
    packages: list[dict] = toml_doc["package"].unwrap()  # type: ignore[assignment] # values are always list[dict]
    return {pkg.pop("name"): pkg for pkg in packages}


def test_pre_commit_versions_are_in_sync(
    pre_commit_config_repos: Mapping, uv_lock_packages: Mapping
):
    repo_package_lookup = {
        "https://github.com/astral-sh/ruff-pre-commit": "ruff",
    }
    for repo, package in repo_package_lookup.items():
        pre_commit_version = Version(pre_commit_config_repos[repo]["rev"])
        uv_lock_version = Version(uv_lock_packages[package]["version"])
        print(f"{package} ->\n  {pre_commit_version=}\n  {uv_lock_version=}\n")
        assert pre_commit_version == uv_lock_version, (
            f"{package} Version mismatch."
            " Make sure the .pre-commit config and uv versions are in sync."
        )


def test_ruff_sync_version_is_in_sync_with_pyproject():
    """
    Ensure the version in ruff_sync.py matches the version in pyproject.toml
    """
    toml_doc = tomlkit.loads(PYPROJECT_TOML.read_text())
    pyproject_version = cast("Any", toml_doc)["project"]["version"]
    assert ruff_sync.__version__ == pyproject_version


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-rEf"])
