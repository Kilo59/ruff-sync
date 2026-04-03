from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from dirty_equals import IsStr

from ruff_sync.cli import Arguments, OutputFormat, _validate_ci_output_format

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
    expected_warning: str | None,
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
        assert any(expected_warning == record.message for record in caplog.records)
    else:
        assert not caplog.records
