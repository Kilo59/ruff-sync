from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import pytest
from dirty_equals import IsStr

from ruff_sync.cli import Arguments, CLIArguments, OutputFormat, _validate_ci_output_format
from ruff_sync.core import Config

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch


@pytest.mark.parametrize(
    ("env_vars", "output_format", "expected_warning"),
    [
        (
            {"GITHUB_ACTIONS": "true"},
            OutputFormat.GITLAB,
            IsStr(regex=".*GitLab output format detected in GitHub Actions environment.*"),
        ),
        (
            {"GITLAB_CI": "true"},
            OutputFormat.GITHUB,
            IsStr(regex=".*GitHub output format detected in GitLab CI environment.*"),
        ),
        (
            {"GITHUB_ACTIONS": "true"},
            OutputFormat.GITHUB,
            None,
        ),
        (
            {"GITLAB_CI": "true"},
            OutputFormat.GITLAB,
            None,
        ),
        (
            {"GITHUB_ACTIONS": "true"},
            OutputFormat.TEXT,
            None,
        ),
        (
            {"GITHUB_ACTIONS": "true", "GITLAB_CI": "true"},
            OutputFormat.GITLAB,
            IsStr(regex=".*GitLab output format detected in GitHub Actions environment.*"),
        ),
        (
            {},
            OutputFormat.GITHUB,
            None,
        ),
    ],
)
def test_validate_ci_output_format(
    monkeypatch: MonkeyPatch,
    caplog: LogCaptureFixture,
    env_vars: dict[str, str],
    output_format: OutputFormat,
    expected_warning: IsStr | None,
) -> None:
    """Test that _validate_ci_output_format logs correct warnings for CI mismatches."""
    # Clear existing env vars and set test ones
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    # Create dummy Arguments
    args = Arguments(
        command="check",
        upstream=(),
        to=None,  # type: ignore[arg-type]
        exclude=None,  # type: ignore[arg-type]
        verbose=0,
        output_format=output_format,
    )

    caplog.clear()
    _validate_ci_output_format(args)

    if expected_warning:
        assert any(record.message == expected_warning for record in caplog.records)
    else:
        assert not caplog.records


@pytest.mark.parametrize(
    ("env_vars", "cli_args", "config", "expected"),
    [
        # CLI takes precedence
        (
            {"GITHUB_ACTIONS": "true"},
            {"output_format": OutputFormat.JSON},
            {},
            OutputFormat.JSON,
        ),
        # Config takes precedence over auto-detection
        (
            {"GITHUB_ACTIONS": "true"},
            {},
            {"output_format": "gitlab"},
            OutputFormat.GITLAB,
        ),
        # Auto-detection: GitHub
        (
            {"GITHUB_ACTIONS": "true"},
            {},
            {},
            OutputFormat.GITHUB,
        ),
        # Auto-detection: GitLab
        (
            {"GITLAB_CI": "true"},
            {},
            {},
            OutputFormat.GITLAB,
        ),
        # Default fallback (returns OutputFormat.TEXT)
        (
            {},
            {},
            {},
            OutputFormat.TEXT,
        ),
        # Unknown config format falls back to auto-detect/default (GitHub in this env)
        (
            {"GITHUB_ACTIONS": "true"},
            {},
            {"output_format": "invalid"},
            OutputFormat.GITHUB,
        ),
        # Explicit CLI TEXT (with CI env)
        (
            {"GITHUB_ACTIONS": "true"},
            {"output_format": OutputFormat.TEXT},
            {},
            OutputFormat.TEXT,
        ),
        # Config TEXT (no CI env)
        (
            {},
            {},
            {"output_format": "text"},
            OutputFormat.TEXT,
        ),
    ],
)
def test_resolve_output_format(
    monkeypatch: MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    env_vars: dict[str, str],
    cli_args: dict[str, Any],
    config: Config,
    expected: OutputFormat,
) -> None:
    """Test that output format is correctly resolved from CLI, config, and environment."""
    from ruff_sync.cli import _resolve_output_format

    # Mock environment
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("GITLAB_CI", raising=False)
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)

    # Mock CLI args
    class MockArgs:
        output_format = None

        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    args: CLIArguments = MockArgs(**cli_args)  # type: ignore[assignment]

    with caplog.at_level(logging.WARNING):
        assert _resolve_output_format(args, config) == expected

    # Only the invalid config case should produce the warning
    if config.get("output_format") == "invalid":
        assert "Unknown output format in config" in caplog.text
        assert "Valid values:" in caplog.text
    else:
        assert "Unknown output format in config" not in caplog.text


def test_main_resolves_output_format(monkeypatch: MonkeyPatch) -> None:
    """End-to-end-ish test for output format resolution in main."""
    from ruff_sync.cli import main

    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    # minimal args to avoid errors before resolution
    monkeypatch.setattr("sys.argv", ["ruff-sync", "check", "https://github.com/org/repo"])

    # We don't actually want to run the whole thing, just see if it resolves correctly.
    # But main calls asyncio.run(check(exec_args)).
    # We can mock 'check' to verify the arguments it receives.
    import ruff_sync.cli

    captured_args: Arguments | None = None

    async def mock_check(args: Arguments) -> int:
        nonlocal captured_args
        captured_args = args
        return 0

    monkeypatch.setattr(ruff_sync.cli, "check", mock_check)
    # Mock pull as well just in case
    monkeypatch.setattr(ruff_sync.cli, "pull", mock_check)

    # Mock get_config to return empty config
    monkeypatch.setattr(ruff_sync.cli, "get_config", lambda _: {})

    main()

    assert captured_args is not None
    assert captured_args.output_format == OutputFormat.GITHUB
