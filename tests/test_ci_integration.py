from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_ci_formatter_selection_manual():
    """Verify that we can manually select CI formatters.

    Note: Auto-detection is not yet implemented.
    See: https://github.com/Kilo59/ruff-sync/issues/142
    """
    from ruff_sync import OutputFormat, get_formatter
    from ruff_sync.formatters import GithubFormatter, GitlabFormatter

    # Verify manual selection works
    github_formatter = get_formatter(OutputFormat.GITHUB)
    assert isinstance(github_formatter, GithubFormatter)

    gitlab_formatter = get_formatter(OutputFormat.GITLAB)
    assert isinstance(gitlab_formatter, GitlabFormatter)


@pytest.mark.asyncio
async def test_output_format_parsing():
    """Test that ArgParser correctly handles output format strings."""
    from ruff_sync import OutputFormat
    from ruff_sync.cli import PARSER

    args = PARSER.parse_args(["check", "http://example.com", "--output-format", "sarif"])
    assert args.output_format == OutputFormat.SARIF

    args = PARSER.parse_args(["check", "http://example.com", "--output-format", "gitlab"])
    assert args.output_format == OutputFormat.GITLAB
