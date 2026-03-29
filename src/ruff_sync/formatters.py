"""Output formatters for CLI results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Protocol
else:
    # Use object as a fallback at runtime if needed, though with Python 3.10+
    # Protocol is always available in typing.
    from typing import Protocol

from ruff_sync.constants import OutputFormat


class ResultFormatter(Protocol):
    """Protocol for output formatters."""

    def info(self, message: str) -> None:
        """Print an informational message."""

    def success(self, message: str) -> None:
        """Print a success message."""

    def error(self, message: str, file_path: str | None = None) -> None:
        """Print an error message."""

    def warning(self, message: str, file_path: str | None = None) -> None:
        """Print a warning message."""


class TextFormatter:
    """Standard text output formatter."""

    def info(self, message: str) -> None:
        """Print an info message."""
        print(message)

    def success(self, message: str) -> None:
        """Print a success message."""
        print(message)

    def error(self, message: str, file_path: str | None = None) -> None:
        """Print an error message."""
        print(message)

    def warning(self, message: str, file_path: str | None = None) -> None:
        """Print a warning message."""
        print(message)


class GithubFormatter:
    """GitHub Actions output formatter.

    Emits `::error::` and `::warning::` workflow commands for inline annotations.
    """

    def info(self, message: str) -> None:
        """Print an info message (standard stdout)."""
        print(message)

    def success(self, message: str) -> None:
        """Print a success message (standard stdout)."""
        print(message)

    def error(self, message: str, file_path: str | None = None) -> None:
        """Print an error message as a GitHub Action error annotation."""
        # Also print the standard string so it shows up cleanly in logs
        print(message)
        # Strip emoji/symbols if any for the raw title, or just use a generic title
        file_arg = f"file={file_path}," if file_path else ""
        # The message is technically what we pass after ::
        # E.g. ::error file=app.js,line=1::Missing semicolon
        clean_msg = message.replace("❌ ", "")
        print(f"::error {file_arg}title=Ruff Sync Error::{clean_msg}")

    def warning(self, message: str, file_path: str | None = None) -> None:
        """Print a warning message as a GitHub Action warning annotation."""
        print(message)
        file_arg = f"file={file_path}," if file_path else ""
        clean_msg = message.replace("⚠️ ", "")
        print(f"::warning {file_arg}title=Ruff Sync Warning::{clean_msg}")


class JsonFormatter:
    """JSON output formatter (stub)."""

    def info(self, message: str) -> None:
        """Stub."""
        print(message)

    def success(self, message: str) -> None:
        """Stub."""
        print(message)

    def error(self, message: str, file_path: str | None = None) -> None:
        """Stub."""
        print(message)

    def warning(self, message: str, file_path: str | None = None) -> None:
        """Stub."""
        print(message)


def get_formatter(format: OutputFormat) -> ResultFormatter:
    """Return the corresponding formatter for the given format."""
    if format == OutputFormat.GITHUB:
        return GithubFormatter()
    if format == OutputFormat.JSON:
        return JsonFormatter()
    return TextFormatter()
