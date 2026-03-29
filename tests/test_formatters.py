from __future__ import annotations

import json
import logging
import pathlib
from typing import TYPE_CHECKING, Any

import pytest

from ruff_sync.constants import OutputFormat
from ruff_sync.formatters import (
    GithubFormatter,
    JsonFormatter,
    TextFormatter,
    get_formatter,
)

if TYPE_CHECKING:
    from ruff_sync.formatters import ResultFormatter


@pytest.fixture(params=[TextFormatter, GithubFormatter, JsonFormatter])
def formatter(request: pytest.FixtureRequest) -> ResultFormatter:
    """Fixture providing instances of all registered formatters."""
    formatter_cls: type[ResultFormatter] = request.param
    return formatter_cls()


class TestFormatterBasics:
    """Common behavior tests for all formatters."""

    @pytest.mark.parametrize(
        "method, message",
        [
            ("note", "test note"),
            ("success", "test success"),
            ("diff", "test diff"),
        ],
    )
    def test_simple_stdout_methods(
        self,
        formatter: ResultFormatter,
        capsys: pytest.CaptureFixture[str],
        method: str,
        message: str,
    ) -> None:
        """Verify methods that primarily output to stdout."""
        getattr(formatter, method)(message)
        captured = capsys.readouterr().out

        if isinstance(formatter, JsonFormatter):
            # diff strip()s input in implementation
            expected_msg = message.strip() if method == "diff" else message
            assert json.loads(captured) == {"level": method, "message": expected_msg}
        else:
            # Text and Github both print raw for these
            assert message in captured

    @pytest.mark.parametrize(
        "method, level",
        [
            ("info", logging.INFO),
            ("error", logging.ERROR),
            ("warning", logging.WARNING),
            ("debug", logging.DEBUG),
        ],
    )
    def test_diagnostic_methods(
        self,
        formatter: ResultFormatter,
        capsys: pytest.CaptureFixture[str],
        caplog: pytest.LogCaptureFixture,
        method: str,
        level: int,
    ) -> None:
        """Verify diagnostic methods (info, error, warning, debug)."""
        message = f"test {method}"

        with caplog.at_level(level, logger="ruff_sync.formatters"):
            getattr(formatter, method)(message)

        captured = capsys.readouterr().out

        if isinstance(formatter, TextFormatter):
            # TextFormatter only logs, never prints diagnostics
            assert captured == ""
            assert message in caplog.text
        elif isinstance(formatter, GithubFormatter):
            # GithubFormatter logs AND prints workflow commands
            assert message in caplog.text
            if method != "info":  # info only logs in GithubFormatter presently
                assert f"::{method}" in captured
        elif isinstance(formatter, JsonFormatter):
            # JsonFormatter only prints JSON
            data = json.loads(captured)
            assert data["level"] == method
            assert data["message"] == message


class TestGithubFormatterSpecifics:
    def test_escape(self) -> None:
        """Verify GitHub-specific character escaping."""
        assert GithubFormatter._escape("a%b\rc\nd") == "a%25b%0Dc%0Ad"
        assert GithubFormatter._escape("a:b,c", is_property=True) == "a%3Ab%2Cc"

    def test_emoji_stripping(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure leading status icons are stripped from GitHub-specific output."""
        fmt = GithubFormatter()
        fmt.error("❌ error msg")
        fmt.warning("⚠️ warning msg")

        captured = capsys.readouterr().out
        assert "title=Ruff Sync Error::error msg" in captured
        assert "title=Ruff Sync Warning::warning msg" in captured

    def test_file_path_metadata(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure file path is propagated in GitHub annotations."""
        fmt = GithubFormatter()
        fmt.error("msg", file_path=pathlib.Path("src/foo.py"))
        assert "file=src/foo.py" in capsys.readouterr().out


class TestJsonFormatterSpecifics:
    @pytest.mark.parametrize("method", ["info", "error", "warning", "debug"])
    def test_metadata_propagation(self, capsys: pytest.CaptureFixture[str], method: str) -> None:
        """Verify file and logger metadata appear in JSON objects for all supportive methods."""
        fmt = JsonFormatter()
        logger = logging.getLogger("custom")
        file_path = pathlib.Path("f.py")

        # Call the method with all possible extras (only error/warning take file_path)
        kwargs: dict[str, Any] = {"logger": logger}
        if method in ("error", "warning"):
            kwargs["file_path"] = file_path

        getattr(fmt, method)("msg", **kwargs)

        data = json.loads(capsys.readouterr().out)
        assert data["logger"] == "custom"
        if method in ("error", "warning"):
            assert data["file"] == "f.py"


def test_get_formatter_factory() -> None:
    """Verify get_formatter returns correct types for all OutputFormat values."""
    assert isinstance(get_formatter(OutputFormat.TEXT), TextFormatter)
    assert isinstance(get_formatter(OutputFormat.JSON), JsonFormatter)
    assert isinstance(get_formatter(OutputFormat.GITHUB), GithubFormatter)
    # Default fallback - ignore error for purposeful type-incorrect input
    assert isinstance(get_formatter("invalid"), TextFormatter)  # type: ignore[arg-type]


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
