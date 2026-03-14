from __future__ import annotations

import pathlib
import subprocess
import sys
from typing import TYPE_CHECKING, Final, NamedTuple

import pytest
import respx
import tomlkit
from httpx import URL

import ruff_sync

# The exact exclude paths from the README Configuration section.
# If you update the README example, update this list to match.
README_EXCLUDES: Final[set[str]] = {
    "target-version",
    "lint.per-file-ignores",
    "lint.ignore",
    "lint.isort.known-first-party",
    "lint.flake8-tidy-imports",
    "lint.pydocstyle.convention",
}

if TYPE_CHECKING:
    from collections.abc import Generator

    from pyfakefs.fake_filesystem import FakeFilesystem
    from pytest import FixtureRequest

TEST_ROOT: Final = pathlib.Path(__file__).parent


def test_manpage():
    """Test that the manpage can be generated with ruff-sync --help with no errors."""
    completed = subprocess.run(
        [sys.executable, "-m", "ruff_sync", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout)
    assert completed.returncode == 0, completed.stderr


LIFECYCLE_TOML_DIR: Final = TEST_ROOT / "lifecycle_tomls"
assert LIFECYCLE_TOML_DIR.exists(), f"{LIFECYCLE_TOML_DIR} does not exist"
LIFECYCLE_GROUPS: Final[set[str]] = {
    "_".join(f.name.split("_")[:-1]) for f in LIFECYCLE_TOML_DIR.glob("*.toml")
}
# Groups that require custom exclude handling — tested separately below.
LIFECYCLE_GROUPS.discard("readme_excludes")


class _PrepEnv(NamedTuple):
    source_path: pathlib.Path
    upstream_url: URL
    expected_toml: str
    respx_mock: respx.MockRouter


@pytest.fixture(params=LIFECYCLE_GROUPS)
def prep_env(fs: FakeFilesystem, request: FixtureRequest) -> Generator[_PrepEnv, None, None]:
    group_name: str = request.param
    fs.add_real_directory(LIFECYCLE_TOML_DIR)

    source_path = pathlib.Path(
        fs.create_file(  # type: ignore[arg-type]
            "my_dir/pyproject.toml",
            contents=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_initial.toml").read_text(),
        ).path
    )
    base_url = "https://example.com"
    upstream_url = URL(f"{base_url}/pyproject.toml")

    with respx.mock(base_url=base_url) as respx_mock:
        respx_mock.get(upstream_url.path).respond(
            200,
            content_type="text/plain",
            content=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_upstream.toml").read_text(),
        )
        yield _PrepEnv(
            source_path=source_path,
            upstream_url=upstream_url,
            expected_toml=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_final.toml").read_text(),
            respx_mock=respx_mock,
        )


@pytest.mark.asyncio
async def test_ruff_sync(prep_env):
    await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=prep_env.upstream_url,
            to=prep_env.source_path,
            exclude=set(),
            verbose=0,
        )
    )

    print(f"Updated toml\n\n{prep_env.source_path.read_text()}")

    assert tomlkit.parse(prep_env.expected_toml) == tomlkit.parse(prep_env.source_path.read_text())
    assert prep_env.expected_toml == prep_env.source_path.read_text()


@pytest.mark.asyncio
async def test_ruff_check(prep_env):
    # 1. Initially it should be out of sync
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            to=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
    )
    # 'no_changes' fixtures are already in sync; all others must be out-of-sync initially.
    if prep_env.expected_toml != prep_env.source_path.read_text():
        assert exit_code != 0, "Expected out-of-sync fixture to return a non-zero exit code"
    #
    # 2. Sync it
    await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=prep_env.upstream_url,
            to=prep_env.source_path,
            exclude=set(),
            verbose=0,
        )
    )
    #
    # 3. Now it MUST be in sync (strictly)
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            to=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
    )
    assert exit_code == 0
    #
    # 4. Now it MUST be in sync (semantically)
    exit_code = await ruff_sync.check(
        ruff_sync.Arguments(
            command="check",
            upstream=prep_env.upstream_url,
            to=prep_env.source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
    )
    assert exit_code == 0


# ---------------------------------------------------------------------------
# README exclude examples — dedicated test with fixture-specific excludes
# ---------------------------------------------------------------------------


@pytest.fixture
def readme_excludes_env(
    fs: FakeFilesystem,
) -> Generator[_PrepEnv, None, None]:
    group_name = "readme_excludes"
    fs.add_real_directory(LIFECYCLE_TOML_DIR)

    source_path = pathlib.Path(
        fs.create_file(  # type: ignore[arg-type]
            "my_dir/pyproject.toml",
            contents=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_initial.toml").read_text(),
        ).path
    )
    base_url = "https://example.com"
    upstream_url = URL(f"{base_url}/pyproject.toml")

    with respx.mock(base_url=base_url) as respx_mock:
        respx_mock.get(upstream_url.path).respond(
            200,
            content_type="text/plain",
            content=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_upstream.toml").read_text(),
        )
        yield _PrepEnv(
            source_path=source_path,
            upstream_url=upstream_url,
            expected_toml=LIFECYCLE_TOML_DIR.joinpath(f"{group_name}_final.toml").read_text(),
            respx_mock=respx_mock,
        )


@pytest.mark.asyncio
async def test_readme_exclude_examples(readme_excludes_env):
    """Verify that the exact exclude paths from the README Configuration
    section correctly preserve local values during a pull.
    """
    env = readme_excludes_env
    await ruff_sync.pull(
        ruff_sync.Arguments(
            command="pull",
            upstream=env.upstream_url,
            to=env.source_path,
            exclude=README_EXCLUDES,
            verbose=0,
        )
    )

    result = env.source_path.read_text()
    print(f"Updated toml\n\n{result}")

    # Semantic check — the merged TOML values should match
    assert tomlkit.parse(env.expected_toml) == tomlkit.parse(result)
    # Exact string check — comments, whitespace, and formatting preserved
    assert env.expected_toml == result


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
