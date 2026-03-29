"""Output formatters for CLI results."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Final, Protocol

if TYPE_CHECKING:
    import pathlib

from ruff_sync.constants import OutputFormat

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)


class ResultFormatter(Protocol):
    """Protocol for output formatters."""

    def note(self, message: str) -> None:
        """Print a status note (unconditional)."""

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print an informational message."""

    def success(self, message: str) -> None:
        """Print a success message."""

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print an error message."""

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print a warning message."""

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print a debug message."""

    def diff(self, diff_text: str) -> None:
        """Print a unified diff between configurations."""


class TextFormatter:
    """Standard text output formatter.

    Delegates diagnostic messages (info, warning, error, debug) to the project logger
     to ensure they benefit from standard logging configuration (colors, streams).
    Primary command feedback (note, success) is printed to stdout.
    """

    def note(self, message: str) -> None:
        """Print a status note to stdout."""
        print(message)

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Log an info message."""
        (logger or LOGGER).info(message)

    def success(self, message: str) -> None:
        """Print a success message to stdout."""
        print(message)

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Log an error message."""
        (logger or LOGGER).error(message)

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Log a warning message."""
        (logger or LOGGER).warning(message)

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Log a debug message."""
        (logger or LOGGER).debug(message)

    def diff(self, diff_text: str) -> None:
        """Print a unified diff directly to stdout."""
        print(diff_text, end="")


class GithubFormatter:
    """GitHub Actions output formatter.

    Emits `::error::` and `::warning::` workflow commands for inline annotations.
    """

    @staticmethod
    def _escape(value: str, is_property: bool = False) -> str:
        r"""Escapes characters for GitHub Actions workflow commands.

        GitHub requires percent-encoding for '%', '\r', and '\n' in all messages.
        Additionally, property values (like file and title) require escaping for ':' and ','.
        """
        escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
        if is_property:
            return escaped.replace(":", "%3A").replace(",", "%2C")
        return escaped

    def note(self, message: str) -> None:
        """Print a status note (standard stdout)."""
        print(message)

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print an info message (delegates to logger)."""
        (logger or LOGGER).info(message)

    def success(self, message: str) -> None:
        """Print a success message (standard stdout)."""
        print(message)

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print an error message as a GitHub Action error annotation."""
        # Delegate standard log output to the logger to preserve context
        (logger or LOGGER).error(message)

        # Strip emoji/symbols if any for the raw title, or just use a generic title
        file_val = self._escape(str(file_path), is_property=True) if file_path else ""
        file_arg = f"file={file_val}," if file_path else ""
        title_val = self._escape("Ruff Sync Error", is_property=True)

        # The message is technically what we pass after ::
        # E.g. ::error file=app.js,line=1::Missing semicolon
        clean_msg = message.removeprefix("❌ ").removeprefix("⚠️ ")
        escaped_msg = self._escape(clean_msg)
        print(f"::error {file_arg}title={title_val}::{escaped_msg}")

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print a warning message as a GitHub Action warning annotation."""
        (logger or LOGGER).warning(message)

        file_val = self._escape(str(file_path), is_property=True) if file_path else ""
        file_arg = f"file={file_val}," if file_path else ""
        title_val = self._escape("Ruff Sync Warning", is_property=True)

        clean_msg = message.removeprefix("❌ ").removeprefix("⚠️ ")
        escaped_msg = self._escape(clean_msg)
        print(f"::warning {file_arg}title={title_val}::{escaped_msg}")

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print a debug message as a GitHub Action debug annotation."""
        (logger or LOGGER).debug(message)
        escaped_msg = self._escape(message)
        print(f"::debug::{escaped_msg}")

    def diff(self, diff_text: str) -> None:
        """Print a unified diff in GitHub Actions logs (standard stdout)."""
        print(diff_text, end="")


class JsonFormatter:
    """JSON output formatter."""

    def note(self, message: str) -> None:
        """Print a status note as JSON."""
        print(json.dumps({"level": "note", "message": message}))

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print an info message as JSON."""
        data = {"level": "info", "message": message}
        if logger:
            data["logger"] = logger.name
        print(json.dumps(data))

    def success(self, message: str) -> None:
        """Print a success message as JSON."""
        print(json.dumps({"level": "success", "message": message}))

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print an error message as JSON."""
        data = {"level": "error", "message": message}
        if file_path:
            data["file"] = str(file_path)
        if logger:
            data["logger"] = logger.name
        print(json.dumps(data))

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Print a warning message as JSON."""
        data = {"level": "warning", "message": message}
        if file_path:
            data["file"] = str(file_path)
        if logger:
            data["logger"] = logger.name
        print(json.dumps(data))

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print a debug message as JSON."""
        data = {"level": "debug", "message": message}
        if logger:
            data["logger"] = logger.name
        print(json.dumps(data))

    def diff(self, diff_text: str) -> None:
        """Print a unified diff as JSON."""
        # Strip trailing newline if any, as it's common in diff text
        print(json.dumps({"level": "diff", "message": diff_text.strip()}))


def get_formatter(output_format: OutputFormat) -> ResultFormatter:
    """Return the corresponding formatter for the given format."""
    if output_format == OutputFormat.GITHUB:
        return GithubFormatter()
    if output_format == OutputFormat.JSON:
        return JsonFormatter()
    return TextFormatter()
