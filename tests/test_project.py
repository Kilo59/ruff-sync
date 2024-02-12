from __future__ import annotations

import logging
import pathlib
import re
import warnings
from pprint import pformat as pf
from typing import TYPE_CHECKING, Final

import httpx
import pytest
import tomlkit
from packaging.version import Version
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from collections.abc import Mapping

yaml = YAML(typ="safe")

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

PROJECT_ROOT: Final = pathlib.Path(__file__).parent.parent
PYPROJECT_TOML: Final = PROJECT_ROOT / "pyproject.toml"


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
def poetry_lock_packages() -> Mapping[str, dict]:
    poetry_lock = PROJECT_ROOT / "poetry.lock"
    toml_doc = tomlkit.loads(poetry_lock.read_text())
    LOGGER.info(f"poetry.lock ->\n {pf(toml_doc, depth=1)[:1000]}...")
    packages: list[dict] = toml_doc["package"].unwrap()  # type: ignore[assignment] # values are always list[dict]
    return {pkg.pop("name"): pkg for pkg in packages}


def test_pre_commit_versions_are_in_sync(
    pre_commit_config_repos: Mapping, poetry_lock_packages: Mapping
):
    repo_package_lookup = {
        "https://github.com/astral-sh/ruff-pre-commit": "ruff",
    }
    for repo, package in repo_package_lookup.items():
        pre_commit_version = Version(pre_commit_config_repos[repo]["rev"])
        poetry_lock_version = Version(poetry_lock_packages[package]["version"])
        print(f"{package} ->\n  {pre_commit_version=}\n  {poetry_lock_version=}\n")
        assert pre_commit_version == poetry_lock_version, (
            f"{package} Version mismatch."
            " Make sure the .pre-commit config and poetry versions are in sync."
        )


@pytest.fixture
def lock_file_poetry_version() -> Version:
    poetry_lock = PROJECT_ROOT / "poetry.lock"
    captured_version: re.Match[str] | None = re.search(
        r"#.*generated by Poetry (?P<version>\d\.\d\.\d)", poetry_lock.read_text().splitlines()[0]
    )
    assert captured_version, "could not parse poetry.lock version"
    return Version(captured_version.group("version"))


class PoetryVersionOutdated(UserWarning):
    pass


@pytest.fixture
def latest_poetry_version(lock_file_poetry_version: Version) -> Version:
    response = httpx.get(
        "https://api.github.com/repos/python-poetry/poetry/releases/latest", timeout=10
    )
    response.raise_for_status()
    latest_version = Version(response.json()["tag_name"])

    if lock_file_poetry_version < latest_version:
        # warning instead of error because we don't want to break the build whenever a new version
        # of poetry is released
        warnings.warn(
            f"The latest version of poetry is {latest_version} but the poetry.lock file was"
            " generated using {lock_file_poetry_version}."
            " Consider upgrading poetry and regenerating the lockfile.",
            category=PoetryVersionOutdated,
            stacklevel=1,
        )
    return latest_version


def test_lockfile_poetry_version(lock_file_poetry_version: Version, latest_poetry_version: Version):
    """
    This test ensures that the poetry.lock file was generated using a recent version of poetry.
    This is important because the lockfile format or dependency resolving strategy could change
    between versions.
    """
    print(f"{lock_file_poetry_version=}")
    print(f"{latest_poetry_version=}")
    assert lock_file_poetry_version >= Version(
        "1.7.1"
    ), "poetry.lock was generated using an older version of poetry"


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-rEf"])
