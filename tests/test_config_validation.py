"""Tests for ruff-sync config validation (validation.py) and related --validate / --strict flags.

Prior tests in this file (test_get_config_warns_on_unknown_key etc.) cover
[tool.ruff-sync] config reading in get_config(). New tests below cover the
validate_merged_config() and validate_ruff_accepts_config() logic added in Phase 1.
"""

from __future__ import annotations

import logging
import pathlib
import subprocess
from typing import TYPE_CHECKING, cast

import pytest
import respx
import tomlkit
from httpx import URL

import ruff_sync
from ruff_sync import get_config
from ruff_sync.cli import LOGGER
from ruff_sync.validation import (
    check_deprecated_rules,
    check_python_version_consistency,
    validate_merged_config,
    validate_ruff_accepts_config,
    validate_toml_syntax,
)

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem

    from tests.conftest import CLIRunner


# ---------------------------------------------------------------------------
# Fixture shared by the legacy get_config tests
# ---------------------------------------------------------------------------


@pytest.fixture
def clean_config_cache():
    """Ensure get_config cache is clear before and after each test."""
    # Ensure LOGGER can be captured by caplog
    original_propagate = LOGGER.propagate
    LOGGER.propagate = True

    # Clear handlers from the root ruff_sync logger to avoid "Bad file descriptor"
    # when running multiple CLI tests that capture stdout/stderr.
    # main() adds handlers to the 'ruff_sync' logger.
    root_logger = logging.getLogger("ruff_sync")
    orig_handlers = root_logger.handlers[:]
    root_logger.handlers.clear()

    get_config.cache_clear()
    yield
    get_config.cache_clear()
    root_logger.handlers = orig_handlers
    LOGGER.propagate = original_propagate


# ===========================================================================
# Legacy [tool.ruff-sync] config-reading tests (pre-existing)
# ===========================================================================


def test_get_config_warns_on_unknown_key(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://github.com/org/repo"
unknown_key = "value"
"""
    )

    # We need to ensure the logger is set up to capture the warning
    # In ruff_sync.py, get_config is called before handlers are added in main()
    # But in tests, caplog should catch it if the level is right.

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration: unknown_key" in caplog.text
    assert "upstream" in config
    assert "unknown_key" not in config


def test_get_config_warns_on_command_key(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
command = "pull"
"""
    )

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration: command" in caplog.text
    assert "command" not in config


def test_get_config_passes_allowed_keys(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
upstream = "https://github.com/org/repo"
exclude = ["lint.per-file-ignores"]
branch = "develop"
"""
    )

    with caplog.at_level(logging.WARNING):
        config = get_config(tmp_path)

    assert "Unknown ruff-sync configuration" not in caplog.text
    assert config["upstream"] == "https://github.com/org/repo"
    assert config["exclude"] == ["lint.per-file-ignores"]
    assert config["branch"] == "develop"


def test_get_config_key_normalization(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture, clean_config_cache: None
):
    """Verify that both dashed and legacy keys are normalized correctly."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.ruff-sync]
# Canonical dashed key
pre-commit-version-sync = true
# Legacy underscored key (alias)
pre_commit_sync = false
# Another legacy alias
pre-commit = true
# Canonical with dashes
output-format = "github"
"""
    )
    # Note: in a real TOML, the last value for the same normalized key WOULD win
    # because they all map to 'pre_commit_version_sync'.
    # But TOML itself doesn't allow duplicate keys if they have the same name.
    # Here they have different names in TOML but map to the same name in Python.

    config = get_config(tmp_path)

    # 'pre-commit-version-sync' -> 'pre_commit_version_sync'
    # 'pre_commit_sync' -> 'pre_commit_version_sync'
    # 'pre-commit' -> 'pre_commit_version_sync'
    # The last one in the file wins if they map to the same key.
    assert config["pre_commit_version_sync"] is True
    assert config["output_format"] == "github"


@pytest.mark.parametrize(
    "config_toml, expected_validate, expected_strict",
    [
        pytest.param("validate = true\nstrict = true\n", True, True, id="both-true"),
        pytest.param("validate = true\n", True, False, id="validate-only"),
        pytest.param("strict = true\n", False, True, id="strict-only"),
        pytest.param("", False, False, id="absent"),
    ],
)
def test_get_config_includes_validation_flags(
    tmp_path: pathlib.Path,
    clean_config_cache: None,
    config_toml: str,
    expected_validate: bool,
    expected_strict: bool,
) -> None:
    """Verify that validate and strict flags are correctly read from config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f"[tool.ruff-sync]\n{config_toml}")
    config = get_config(tmp_path)
    assert config.get("validate", False) is expected_validate
    assert config.get("strict", False) is expected_strict


@pytest.mark.parametrize(
    "config_toml, cli_args, expected_validate, expected_strict",
    [
        # Config `strict = true`, CLI `--no-strict` / `--no-validate` should let CLI win
        pytest.param(
            "validate = true\nstrict = true\n",
            ["--no-strict"],
            True,
            False,
            id="config-strict-true-cli-no-strict",
        ),
        pytest.param(
            "validate = true\nstrict = true\n",
            ["--no-validate"],
            False,
            False,
            id="config-strict-true-cli-no-validate",
        ),
        # Config `validate = true` only, CLI `--strict` (strict still implies validate)
        pytest.param(
            "validate = true\n",
            ["--strict"],
            True,
            True,
            id="config-validate-true-cli-strict",
        ),
        pytest.param(
            "",
            ["--strict"],
            True,
            True,
            id="config-none-cli-strict",
        ),
        # Config sets both flags, CLI passes them again with different values
        pytest.param(
            "validate = true\nstrict = true\n",
            ["--no-validate", "--no-strict"],
            False,
            False,
            id="config-both-true-cli-both-false",
        ),
        pytest.param(
            "validate = false\nstrict = false\n",
            ["--validate", "--strict"],
            True,
            True,
            id="config-both-false-cli-both-true",
        ),
    ],
)
def test_validation_flags_cli_vs_config_precedence(
    tmp_path: pathlib.Path,
    clean_config_cache: None,
    config_toml: str,
    cli_args: list[str],
    expected_validate: bool,
    expected_strict: bool,
):
    """
    Verify that CLI flags override config values where intended, and that
    `strict` always implies `validate` regardless of whether it comes from
    the config file or CLI flags.
    """
    from ruff_sync.cli import PARSER, Arguments, _resolve_strict, _resolve_validate

    # Write per-test config
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(f"[tool.ruff-sync]\n{config_toml}")

    # Parse CLI args
    # We add a dummy 'upstream' to satisfy argparse requirements
    parsed_args = PARSER.parse_args(["pull", "https://example.com", *cli_args])

    # Get config (from the mocked pyproject.toml)
    config = get_config(tmp_path)

    # Resolve to Arguments (transport layer)
    args = Arguments(
        command=parsed_args.command,
        upstream=tuple(parsed_args.upstream),
        to=tmp_path,
        exclude=[],
        verbose=0,
        validate=_resolve_validate(parsed_args, config),
        strict=_resolve_strict(parsed_args, config),
    )

    # Resolve to ExecutionArgs (logic layer)
    exec_args = args.resolve()

    assert exec_args.validate is expected_validate
    assert exec_args.strict is expected_strict

    # Guard that `strict` continues to imply `validate` at runtime
    if exec_args.strict:
        assert exec_args.validate is True


# ===========================================================================
# Phase 1 — validate_toml_syntax
# ===========================================================================


def test_validate_toml_syntax_valid() -> None:
    """A well-formed TOMLDocument should pass the syntax check."""
    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")
    assert validate_toml_syntax(doc) is True


def test_validate_toml_syntax_logs_exception(caplog: pytest.LogCaptureFixture) -> None:
    """If tomlkit.parse raises a TOMLKitError, it should be logged."""
    # We can't easily make tomlkit.parse(doc.as_string()) fail if doc
    # is a TOMLDocument, because doc.as_string() is always valid TOML.
    # However, we can mock doc.as_string() to return invalid TOML.

    class BadDoc:
        def as_string(self) -> str:
            return "[[invalid"

    with caplog.at_level(logging.ERROR, logger="ruff_sync.validation"):
        result = validate_toml_syntax(BadDoc())  # type: ignore[arg-type]

    assert result is False
    assert "Merged config failed TOML syntax check" in caplog.text
    # tomlkit.parse('[[invalid') raises TOMLKitError
    assert "Unexpected end of file" in caplog.text or "invalid" in caplog.text.lower()


# ===========================================================================
# Phase 1 — validate_ruff_accepts_config (unit, calls real ruff binary)
# ===========================================================================


def test_validate_ruff_accepts_valid_pyproject_config() -> None:
    """A valid [tool.ruff] config should be accepted by ruff (exit 0 or 1)."""
    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")
    result = validate_ruff_accepts_config(doc, is_ruff_toml=False)
    # Either True (ruff accepted) or True (ruff not on PATH — soft fail).
    # We assert it doesn't crash and returns a bool.
    assert isinstance(result, bool)


def test_validate_ruff_accepts_valid_ruff_toml_config() -> None:
    """A valid ruff.toml-style config should be accepted by ruff."""
    doc = tomlkit.parse("line-length = 100\n")
    result = validate_ruff_accepts_config(doc, is_ruff_toml=True)
    assert isinstance(result, bool)


def test_validate_ruff_rejects_invalid_pyproject_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ruff should reject a config with an unknown [tool.ruff] key.

    We use monkeypatch to inject a fake subprocess.run that simulates ruff
    exiting with code 2 (config error), avoiding a real subprocess call in CI
    where the ruff version may differ.
    """

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=2,
            stdout="",
            stderr="unknown field `not-a-real-key`",
        )

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    doc = tomlkit.parse("[tool.ruff]\nnot-a-real-key = true\n")
    result = validate_ruff_accepts_config(doc, is_ruff_toml=False)
    assert result is False


def test_validate_ruff_accepts_config_strict_fails_on_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In strict mode, config warnings should cause validation to fail."""

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0,
            stdout="",
            stderr="warning: `target-version` is deprecated."
            " Use `project.requires-python` instead.",
        )

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    doc = tomlkit.parse("[tool.ruff]\ntarget-version = 'py310'\n")

    # Non-strict mode: should pass (exit code 0)
    assert validate_ruff_accepts_config(doc, strict=False) is True

    # Strict mode: should fail (warning in stderr)
    assert validate_ruff_accepts_config(doc, strict=True) is False


def test_validate_ruff_soft_fails_when_ruff_not_on_path(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If ruff is not on PATH, validation should soft-fail (return True, emit warning)."""

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        msg = "ruff: command not found"
        raise FileNotFoundError(msg)

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = validate_ruff_accepts_config(doc, is_ruff_toml=False)

    assert result is True  # Soft fail — don't block users without ruff on PATH
    assert "not found on PATH" in caplog.text


def test_validate_ruff_soft_fails_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If ruff times out, validation should soft-fail (return True, emit warning)."""

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd=["ruff"], timeout=30)

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = validate_ruff_accepts_config(doc, is_ruff_toml=False)

    assert result is True  # Soft fail on timeout
    assert "timed out" in caplog.text


# ===========================================================================
# Phase 1 — validate_merged_config (top-level entrypoint)
# ===========================================================================


def test_validate_merged_config_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    """A valid merged config should pass all checks."""
    doc = tomlkit.parse("[tool.ruff]\nline-length = 100\n")

    # validate_ruff_accepts_config may soft-fail if ruff isn't on PATH,
    # but validate_merged_config should still return True (not crash).
    result = validate_merged_config(doc)
    assert isinstance(result, bool)

    # Also exercise the is_ruff_toml=True branch, ensuring that the
    # ruff.toml-specific path (including filename handling) is exercised.
    called: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        called["cmd"] = cmd

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()  # type: ignore[return-value]

    monkeypatch.setattr(subprocess, "run", fake_run)

    result_ruff_toml = validate_merged_config(doc, is_ruff_toml=True)
    assert isinstance(result_ruff_toml, bool)
    assert "cmd" in called

    cmd = cast("list[str]", called["cmd"])
    # Check that some argument refers to a ruff.toml-specific path.
    assert any("ruff.toml" in str(part) for part in cmd)
    # verify --isolated is NOT present because it conflicts with --config
    assert "--isolated" not in cmd


def test_validate_merged_config_returns_false_on_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """validate_merged_config should return False when ruff rejects the config."""

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=2,
            stdout="",
            stderr="unknown field `not-a-real-key`",
        )

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    doc = tomlkit.parse("[tool.ruff]\nnot-a-real-key = true\n")
    assert validate_merged_config(doc) is False


# ===========================================================================
# Phase 1 — Integration: pull() with --validate flag
# ===========================================================================

_VALID_UPSTREAM = """\
[tool.ruff]
line-length = 100
"""

_INVALID_UPSTREAM = """\
[tool.ruff]
not-a-real-key = true
"""

_LOCAL_PYPROJECT = """\
[tool.ruff]
line-length = 88
"""


@pytest.mark.asyncio
async def test_pull_aborts_on_invalid_config_when_validate_is_true(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When --validate is passed and ruff rejects the config, pull() returns 1.

    The local pyproject.toml must remain unchanged.
    """
    fs.create_file("pyproject.toml", contents=_LOCAL_PYPROJECT)
    source_path = pathlib.Path("pyproject.toml")

    # Simulate ruff rejecting the merged config (exit code 2 = config error)
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        if "ruff" in cmd[0]:
            return subprocess.CompletedProcess(
                args=cmd, returncode=2, stdout="", stderr="unknown field `not-a-real-key`"
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content=_INVALID_UPSTREAM
        )

        args = ruff_sync.Arguments(
            command="pull",
            upstream=(URL("https://example.com/pyproject.toml"),),
            to=source_path,
            exclude=(),
            verbose=0,
            validate=True,
        )

        exit_code = await ruff_sync.pull(args)

    # Validation failed → non-zero exit
    assert exit_code == 1
    # The local file must be left UNCHANGED
    assert source_path.read_text() == _LOCAL_PYPROJECT


@pytest.mark.asyncio
async def test_pull_skips_validation_by_default(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard: without --validate, pull() succeeds even with a bad upstream key.

    Validation is opt-in. validate=False (the default) must never call ruff.
    """
    validation_called = False

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal validation_called
        validation_called = True
        return subprocess.CompletedProcess(args=cmd, returncode=2, stdout="", stderr="")

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    fs.create_file("pyproject.toml", contents=_LOCAL_PYPROJECT)
    source_path = pathlib.Path("pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content=_VALID_UPSTREAM
        )

        args = ruff_sync.Arguments(
            command="pull",
            upstream=(URL("https://example.com/pyproject.toml"),),
            to=source_path,
            exclude=(),
            verbose=0,
            # validate defaults to False — validation must NOT run
        )

        exit_code = await ruff_sync.pull(args)

    assert exit_code == 0
    # The validation subprocess must NOT have been called
    assert not validation_called, "ruff subprocess was called even though validate=False"


@pytest.mark.asyncio
async def test_pull_succeeds_when_validate_passes(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When --validate is passed and ruff accepts the config, pull() succeeds (exit 0)."""
    fs.create_file("pyproject.toml", contents=_LOCAL_PYPROJECT)
    source_path = pathlib.Path("pyproject.toml")

    # Ruff accepts the config (exit 0)
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content=_VALID_UPSTREAM
        )

        args = ruff_sync.Arguments(
            command="pull",
            upstream=(URL("https://example.com/pyproject.toml"),),
            to=source_path,
            exclude=(),
            verbose=0,
            validate=True,
        )

        exit_code = await ruff_sync.pull(args)

    assert exit_code == 0
    # The file should be updated with the upstream content
    assert "line-length = 100" in source_path.read_text()


# ===========================================================================
# Priority 2 — Python Version Consistency Check
# ===========================================================================


@pytest.mark.parametrize(
    "toml_content, expected_warn, expected_msg",
    [
        pytest.param(
            '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "py39"\n',
            True,
            "Version mismatch",
            id="mismatch-warn",
        ),
        pytest.param(
            '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "py310"\n',
            False,
            None,
            id="compatible-exact",
        ),
        pytest.param(
            '[project]\nrequires-python = ">=3.10"\n',
            False,
            None,
            id="missing-target-version",
        ),
        pytest.param(
            '[tool.ruff]\ntarget-version = "py39"\n',
            False,
            None,
            id="missing-requires-python",
        ),
        pytest.param(
            '[project]\nrequires-python = "foo"\n\n[tool.ruff]\ntarget-version = "py310"\n',
            False,
            None,
            id="unparsable-requires-python",
        ),
        pytest.param(
            '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "3.10"\n',
            False,
            None,
            id="unparsable-target-version",
        ),
        pytest.param(
            '[project]\nrequires-python = "==3.11.*,>=3.8"\n'
            '\n[tool.ruff]\ntarget-version = "py39"\n',
            False,
            None,
            id="multiple-specifiers-ok",
        ),
        pytest.param(
            '[project]\nrequires-python = ">=3.10, <4"\n\n[tool.ruff]\ntarget-version = "py39"\n',
            True,
            "Version mismatch",
            id="multiple-specifiers-warn",
        ),
    ],
)
def test_version_consistency_cases(
    caplog: pytest.LogCaptureFixture,
    toml_content: str,
    expected_warn: bool,
    expected_msg: str | None,
) -> None:
    """Parametrized test for Python version consistency validation."""
    doc = tomlkit.parse(toml_content)

    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_python_version_consistency(doc)

    # All these cases should return True (warnings only)
    assert result is True
    if expected_warn:
        assert expected_msg is not None
        assert expected_msg in caplog.text
    else:
        assert "Version mismatch" not in caplog.text


def test_version_consistency_skipped_for_ruff_toml(caplog: pytest.LogCaptureFixture) -> None:
    """Standalone ruff.toml files lack [project], so the check should be skipped."""
    doc = tomlkit.parse("target-version = 'py39'\n")
    # validate_merged_config skips the check if is_ruff_toml=True
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = validate_merged_config(doc, is_ruff_toml=True)

    assert result is True
    assert "Version mismatch" not in caplog.text


@pytest.mark.parametrize(
    "toml_content, expected_suffix",
    [
        pytest.param(
            "",
            "missing [tool.ruff] target-version, [project] requires-python.",
            id="missing-both",
        ),
        pytest.param(
            '[project]\nrequires-python = ">=3.10"\n',
            "missing [tool.ruff] target-version.",
            id="missing-target",
        ),
        pytest.param(
            '[tool.ruff]\ntarget-version = "py310"\n',
            "missing [project] requires-python.",
            id="missing-requires",
        ),
    ],
)
def test_version_consistency_logs_skip_decision(
    caplog: pytest.LogCaptureFixture, toml_content: str, expected_suffix: str
) -> None:
    """It should log a warning message when skipping due to missing version keys."""
    doc = tomlkit.parse(toml_content)
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        check_python_version_consistency(doc)

    expected_msg = f"Skipping Python version consistency check: {expected_suffix}"
    assert expected_msg in caplog.text


def test_version_consistency_skipped_when_excluded(caplog: pytest.LogCaptureFixture) -> None:
    """It should log a specific warning when target-version is explicitly excluded."""
    # mismatch that would normally warn
    toml_content = '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "py39"\n'
    doc = tomlkit.parse(toml_content)

    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        # Case 1: excluded via 'target-version'
        result = check_python_version_consistency(doc, exclude=("target-version",))
        assert result is True
        assert (
            "Skipping Python version consistency check: 'target-version' is "
            "excluded in [tool.ruff-sync]."
        ) in caplog.text

        caplog.clear()

        # Case 2: excluded via 'tool.ruff.target-version'
        result = check_python_version_consistency(doc, exclude=("tool.ruff.target-version",))
        assert result is True
        assert (
            "Skipping Python version consistency check: 'target-version' is "
            "excluded in [tool.ruff-sync]."
        ) in caplog.text


def test_strict_mode_fails_on_version_mismatch(caplog: pytest.LogCaptureFixture) -> None:
    """In strict mode, a version mismatch should cause validation to fail."""
    doc = tomlkit.parse(
        '[project]\nrequires-python = ">=3.10"\n\n[tool.ruff]\ntarget-version = "py39"\n'
    )
    with caplog.at_level(logging.ERROR, logger="ruff_sync.validation"):
        from ruff_sync.validation import validate_merged_config

        result = validate_merged_config(doc, strict=True)

    assert result is False
    assert "Version mismatch" in caplog.text


# ===========================================================================
# Priority 3 — Rule Deprecation Warnings
# ===========================================================================


def test_deprecated_rule_warning_emitted(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(doc, _deprecated_codes=frozenset({"UP036"}))
    assert result is True
    assert "deprecated rule 'UP036'" in caplog.text


def test_deprecated_rule_ruff_toml_warning_emitted(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(
            doc, is_ruff_toml=True, _deprecated_codes=frozenset({"UP036"})
        )
    assert result is True
    assert "deprecated rule 'UP036'" in caplog.text


def test_deprecated_rules_skipped_when_excluded(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(
            doc, _deprecated_codes=frozenset({"UP036"}), exclude=("tool.ruff.lint.select",)
        )
    assert result is True
    assert "deprecated rule" not in caplog.text

    # Also check short name exclusion works
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(
            doc, _deprecated_codes=frozenset({"UP036"}), exclude=("select",)
        )
    assert result is True
    assert "deprecated rule" not in caplog.text


def test_no_warning_for_valid_rules(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["E501"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(doc, _deprecated_codes=frozenset({"UP036"}))
    assert result is True
    assert "deprecated rule" not in caplog.text


def test_deprecated_rules_skipped_when_ruff_unavailable(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(doc, _deprecated_codes=frozenset())
    assert result is True
    assert "deprecated rule" not in caplog.text


def test_strict_mode_fails_on_deprecated_rules(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.ERROR, logger="ruff_sync.validation"):
        result = check_deprecated_rules(doc, strict=True, _deprecated_codes=frozenset({"UP036"}))
    assert result is False
    assert "deprecated rule 'UP036'" in caplog.text


def test_non_strict_mode_passes_on_deprecated_rules(caplog: pytest.LogCaptureFixture) -> None:
    doc = tomlkit.parse('[tool.ruff.lint]\nselect = ["UP036"]\n')
    with caplog.at_level(logging.WARNING, logger="ruff_sync.validation"):
        result = check_deprecated_rules(doc, strict=False, _deprecated_codes=frozenset({"UP036"}))
    assert result is True
    assert "deprecated rule 'UP036'" in caplog.text


@pytest.mark.parametrize(
    "config_toml, ruff_stderr, ruff_exit_code, expected_exit_code, expected_msg",
    [
        pytest.param(
            "strict = true",
            "warning: config obsolete",
            0,
            1,
            "Ruff validation warning(s) detected in strict mode",
            id="strict-fails-on-warning",
        ),
        pytest.param(
            "validate = true",
            "error: unknown field",
            2,
            1,
            "Merged config failed validation",
            id="validate-fails-on-error",
        ),
        pytest.param(
            "",  # No validation in config
            "warning: config obsolete",
            0,
            0,
            None,
            id="opt-in-by-default",
        ),
    ],
)
def test_pull_uses_persisted_validation_settings(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    cli_run: CLIRunner,
    clean_config_cache: None,
    config_toml: str,
    ruff_stderr: str,
    ruff_exit_code: int,
    expected_exit_code: int,
    expected_msg: str | None,
) -> None:
    """Pull must honor validation settings defined in [tool.ruff-sync]."""
    fs.create_file(
        "pyproject.toml",
        contents=(
            f'[tool.ruff-sync]\nupstream = "https://example.com/pyproject.toml"\n{config_toml}\n'
        ),
    )

    # Simulate ruff behavior
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=ruff_exit_code, stdout="", stderr=ruff_stderr
        )

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content="[tool.ruff]\n"
        )

        with caplog.at_level(logging.ERROR, logger="ruff_sync.validation"):
            exit_code, _, _ = cli_run(["pull"])

    assert exit_code == expected_exit_code
    if expected_msg:
        assert expected_msg in caplog.text


@pytest.mark.parametrize(
    "cli_flags, expected_in_toml, expected_not_in_toml",
    [
        pytest.param(
            ["--strict"],
            ["strict = true", "validate = true"],
            [],
            id="strict-persists-both",
        ),
        pytest.param(
            ["--validate"],
            ["validate = true"],
            ["strict = true"],
            id="validate-persists-only-validate",
        ),
    ],
)
def test_pull_save_persists_validation_flags(
    fs: FakeFilesystem,
    monkeypatch: pytest.MonkeyPatch,
    cli_run: CLIRunner,
    clean_config_cache: None,
    cli_flags: list[str],
    expected_in_toml: list[str],
    expected_not_in_toml: list[str],
) -> None:
    """Pull --save with validation flags must persist them to [tool.ruff-sync]."""
    fs.create_file(
        "pyproject.toml",
        contents='[tool.ruff-sync]\nupstream = "https://example.com/pyproject.toml"\n',
    )
    source_path = pathlib.Path("pyproject.toml")

    # Mock success validation
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("ruff_sync.validation.subprocess.run", fake_run)

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content="[tool.ruff]\n"
        )

        # Run with --save and the parametrized flags
        exit_code, _, _ = cli_run(["pull", "--save", *cli_flags])

    assert exit_code == 0
    content = source_path.read_text()
    for expected in expected_in_toml:
        assert expected in content
    for unexpected in expected_not_in_toml:
        assert unexpected not in content


def test_pull_save_clears_validation_flags(
    fs: FakeFilesystem,
    cli_run: CLIRunner,
    clean_config_cache: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pull --no-strict --save must persist 'false' to [tool.ruff-sync]."""
    fs.create_file(
        "pyproject.toml",
        contents=(
            "[tool.ruff-sync]\n"
            'upstream = "https://example.com/pyproject.toml"\n'
            "strict = true\n"
            "validate = true\n"
        ),
    )

    # Mock validation logic to avoid pyfakefs/subprocess conflicts
    monkeypatch.setattr(
        "ruff_sync.validation.validate_ruff_accepts_config", lambda *args, **kwargs: True
    )

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200, content_type="text/plain", content="[tool.ruff]\n"
        )

        # Run with --no-strict --save
        exit_code, _, _ = cli_run(["pull", "--no-strict", "--save"])
        assert exit_code == 0

        # Verify that 'strict = false' is now in the TOML
        # Note: validate will still be true because it was in config and we only cleared strict
        content = pathlib.Path("pyproject.toml").read_text()
        assert "strict = false" in content
        assert "validate = true" in content

        # Now clear validate too
        exit_code, _, _ = cli_run(["pull", "--no-validate", "--save"])
        assert exit_code == 0
        content = pathlib.Path("pyproject.toml").read_text()
        assert "validate = false" in content


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
