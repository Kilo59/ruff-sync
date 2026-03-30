"""Output formatters for CLI results."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import TYPE_CHECKING, Final, Literal, Protocol, TypedDict

if TYPE_CHECKING:
    import pathlib

from ruff_sync.constants import OutputFormat

LOGGER: Final[logging.Logger] = logging.getLogger(__name__)

_DEFAULT_CHECK_NAME: Final[str] = "ruff-sync/config-drift"


class ResultFormatter(Protocol):
    """Protocol for output formatters.

    Streaming formatters (Text, GitHub, JSON) implement ``note`` / ``info`` /
    ``success`` / ``error`` / ``warning`` / ``debug`` / ``diff`` and provide a
    no-op ``finalize``.

    Accumulating formatters (GitLab, SARIF) collect issues during the run and
    write their structured report in ``finalize``.  ``finalize`` is always
    called by the CLI in a ``try...finally`` block, so all formatters receive
    it unconditionally.
    """

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
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print an error message.

        Args:
            message: Human-readable description of the issue.
            file_path: Path to the file that contains the issue.
            logger: Optional logger to use instead of the module logger.
            check_name: Machine-readable rule ID (used by structured formatters).
            drift_key: Dotted TOML key that drifted, e.g. ``"lint.select"``.
                Used by structured formatters to build stable fingerprints.
        """

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print a warning message.

        Args:
            message: Human-readable description of the issue.
            file_path: Path to the file that contains the issue.
            logger: Optional logger to use instead of the module logger.
            check_name: Machine-readable rule ID (used by structured formatters).
            drift_key: Dotted TOML key that drifted, e.g. ``"lint.select"``.
                Used by structured formatters to build stable fingerprints.
        """

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print a debug message."""

    def diff(self, diff_text: str) -> None:
        """Print a unified diff between configurations.

        Note:
            Structured (accumulating) formatters intentionally ignore this
            method — diffs are not representable in JSON report schemas.
        """

    def finalize(self) -> None:
        """Finalize and flush all output.

        Streaming formatters (Text, GitHub, JSON) implement this as a no-op.
        Accumulating formatters (GitLab, SARIF) write their collected report
        here.  The CLI calls this unconditionally inside a ``try...finally``
        block so it is always executed, even when an exception occurred.
        """


class TextFormatter:
    """Standard text output formatter.

    Delegates diagnostic messages (info, warning, error, debug) to the project
    logger to ensure they benefit from standard logging configuration (colors,
    streams).  Primary command feedback (note, success) is printed to stdout.
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
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Log an error message."""
        (logger or LOGGER).error(message)

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Log a warning message."""
        (logger or LOGGER).warning(message)

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Log a debug message."""
        (logger or LOGGER).debug(message)

    def diff(self, diff_text: str) -> None:
        """Print a unified diff directly to stdout."""
        print(diff_text, end="")

    def finalize(self) -> None:
        """No-op for streaming formatters."""


class GithubFormatter:
    """GitHub Actions output formatter.

    Emits ``::error::`` and ``::warning::`` workflow commands for inline
    annotations.
    """

    @staticmethod
    def _escape(value: str, is_property: bool = False) -> str:
        r"""Escapes characters for GitHub Actions workflow commands.

        GitHub requires percent-encoding for '%', '\r', and '\n' in all
        messages.  Additionally, property values (like file and title) require
        escaping for ':' and ','.
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
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print an error message as a GitHub Action error annotation."""
        # Delegate standard log output to the logger to preserve context
        (logger or LOGGER).error(message)

        file_val = self._escape(str(file_path), is_property=True) if file_path else ""
        file_arg = f"file={file_val},line=1," if file_path else ""
        title_val = self._escape("Ruff Sync Error", is_property=True)

        clean_msg = message.removeprefix("❌ ").removeprefix("⚠️ ")
        escaped_msg = self._escape(clean_msg)
        print(f"::error {file_arg}title={title_val}::{escaped_msg}")

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print a warning message as a GitHub Action warning annotation."""
        (logger or LOGGER).warning(message)

        file_val = self._escape(str(file_path), is_property=True) if file_path else ""
        file_arg = f"file={file_val},line=1," if file_path else ""
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

    def finalize(self) -> None:
        """No-op for streaming formatters."""


class JsonFormatter:
    """JSON output formatter (newline-delimited JSON, one record per line)."""

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
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print an error message as JSON."""
        data = {"level": "error", "message": message}
        if file_path:
            data["file"] = str(file_path)
        if logger:
            data["logger"] = logger.name
        if drift_key:
            data["drift_key"] = drift_key
        print(json.dumps(data))

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Print a warning message as JSON."""
        data = {"level": "warning", "message": message}
        if file_path:
            data["file"] = str(file_path)
        if logger:
            data["logger"] = logger.name
        if drift_key:
            data["drift_key"] = drift_key
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

    def finalize(self) -> None:
        """No-op for streaming formatters."""


class GitlabLines(TypedDict):
    """GitLab Code Quality report lines."""

    begin: int


class GitlabLocation(TypedDict):
    """GitLab Code Quality report location."""

    path: str
    lines: GitlabLines


class GitlabIssue(TypedDict):
    """GitLab Code Quality report issue."""

    description: str
    check_name: str
    fingerprint: str
    severity: Literal["info", "minor", "major", "critical", "blocker"]
    location: GitlabLocation


class GitlabFormatter:
    """GitLab Code Quality report formatter.

    Accumulates issues during the run and writes a single valid JSON array to
    stdout in ``finalize()``.  The CI job redirects stdout to a file::

        ruff-sync check --output-format gitlab > gl-code-quality-report.json

    An empty array (``[]``) is emitted when no issues were collected, which
    signals to GitLab that previously reported issues are now resolved.

    Fingerprints are deterministic MD5 hashes so GitLab can track whether an
    issue was introduced or resolved between branches.
    """

    def __init__(self) -> None:
        """Initialise an empty issue list."""
        self._issues: list[GitlabIssue] = []

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def note(self, message: str) -> None:
        """No-op: status notes are not representable in the Code Quality schema."""

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Delegate to logger only; not included in the structured report."""
        (logger or LOGGER).info(message)

    def success(self, message: str) -> None:
        """No-op: success messages are not representable in the Code Quality schema."""

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Accumulate a major-severity Code Quality issue."""
        (logger or LOGGER).error(message)
        self._issues.append(
            self._make_issue(
                description=message,
                check_name=check_name,
                severity="major",
                file_path=file_path,
                drift_key=drift_key,
            )
        )

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Accumulate a minor-severity Code Quality issue."""
        (logger or LOGGER).warning(message)
        self._issues.append(
            self._make_issue(
                description=message,
                check_name=check_name,
                severity="minor",
                file_path=file_path,
                drift_key=drift_key,
            )
        )

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Delegate to logger only; not included in the structured report."""
        (logger or LOGGER).debug(message)

    def diff(self, diff_text: str) -> None:
        """Ignored by structured formatters — diffs are not representable in JSON report schemas."""

    def finalize(self) -> None:
        """Write the collected issues as a GitLab Code Quality JSON array to stdout.

        Always produces valid JSON: an empty array ``[]`` when no issues were
        collected (signals resolution of previously reported issues to GitLab).
        """
        print(json.dumps(self._issues, indent=2))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_issue(
        self,
        description: str,
        check_name: str,
        severity: Literal["info", "minor", "major", "critical", "blocker"],
        file_path: pathlib.Path | None,
        drift_key: str | None,
    ) -> GitlabIssue:
        """Build a single Code Quality issue object."""
        # location.path must be relative to the repo root (no absolute paths).
        path = str(file_path) if file_path else "pyproject.toml"
        return {
            "description": description,
            "check_name": check_name,
            "fingerprint": self._make_fingerprint(path, drift_key),
            "severity": severity,
            "location": {"path": path, "lines": {"begin": 1}},
        }

    @staticmethod
    def _make_fingerprint(path: str, drift_key: str | None) -> str:
        """Return a stable MD5 fingerprint for a Code Quality issue.

        The fingerprint must be deterministic (same inputs → same output on
        every pipeline run) so GitLab can track introduced vs resolved issues.
        Never include timestamps, UUIDs, or any other runtime-variable data.
        """
        raw = f"ruff-sync:drift:{path}:{drift_key}" if drift_key else f"ruff-sync:drift:{path}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324


def get_formatter(output_format: OutputFormat) -> ResultFormatter:
    """Return the corresponding formatter for the given format."""
    match output_format:
        case OutputFormat.TEXT:
            return TextFormatter()
        case OutputFormat.GITHUB:
            return GithubFormatter()
        case OutputFormat.JSON:
            return JsonFormatter()
        case OutputFormat.GITLAB:
            return GitlabFormatter()
