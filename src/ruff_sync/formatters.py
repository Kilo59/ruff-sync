"""Output formatters for CLI results."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
from typing import Any, Final, Literal, Protocol, TypedDict

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


class GithubIssue(TypedDict):
    """GitHub Action output issue."""

    level: Literal["error", "warning"]
    message: str
    file_path: pathlib.Path | None
    check_name: str
    drift_key: str | None


class GithubFormatter:
    """GitHub Actions output formatter.

    Emits ``::error::`` and ``::warning::`` workflow commands for inline
    annotations, and writes a Markdown report to ``GITHUB_STEP_SUMMARY``.
    """

    def __init__(self) -> None:
        """Initialise an empty issue list."""
        self._errors: list[GithubIssue] = []
        self._warnings: list[GithubIssue] = []

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
        """Accumulate an error-level finding."""
        # Delegate standard log output to the logger to preserve context
        (logger or LOGGER).error(message)
        self._errors.append(
            {
                "level": "error",
                "message": message,
                "file_path": file_path,
                "check_name": check_name,
                "drift_key": drift_key,
            }
        )

    def warning(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Accumulate a warning-level finding."""
        (logger or LOGGER).warning(message)
        self._warnings.append(
            {
                "level": "warning",
                "message": message,
                "file_path": file_path,
                "check_name": check_name,
                "drift_key": drift_key,
            }
        )

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Print a debug message as a GitHub Action debug annotation."""
        (logger or LOGGER).debug(message)
        escaped_msg = self._escape(message)
        print(f"::debug::{escaped_msg}")

    def diff(self, diff_text: str) -> None:
        """Print a unified diff in GitHub Actions logs (standard stdout)."""
        print(diff_text, end="")

    def finalize(self) -> None:
        """Finalize and emit all accumulated issues as GitHub workflow commands.

        If multiple issues exist for a single file/level, they are combined into
        a single multi-line annotation to reduce visual noise.

        A Markdown summary is also written to ``GITHUB_STEP_SUMMARY`` if the
        environment variable is set.
        """
        all_issues = self._errors + self._warnings

        # 1. Emit Inline Annotations
        self._emit_annotations()

        # 2. Write Step Summary
        self._write_summary(all_issues)

    def _emit_annotations(self) -> None:
        """Group and emit issues as GitHub Action workflow commands."""
        for level, issues in [("error", self._errors), ("warning", self._warnings)]:
            # Group by file_path
            by_file: dict[str, list[GithubIssue]] = {}
            for issue in issues:
                file_key = str(issue["file_path"] or "")
                by_file.setdefault(file_key, []).append(issue)

            for file_path_str, file_issues in by_file.items():
                if not file_issues:
                    continue

                title_prefix = "Error" if level == "error" else "Warning"
                title_val = self._escape(f"Ruff Sync {title_prefix}", is_property=True)
                file_val = self._escape(file_path_str, is_property=True) if file_path_str else ""
                file_arg = f"file={file_val},line=1," if file_val else ""

                if len(file_issues) == 1:
                    issue = file_issues[0]
                    clean_msg = issue["message"].removeprefix("❌ ").removeprefix("⚠️ ")
                    escaped_msg = self._escape(clean_msg)
                else:
                    # Combine into a single bulleted annotation
                    combined_msg = (
                        f"Multiple ruff-sync {level}s in {file_path_str or 'pyproject.toml'}:"
                    )
                    for issue in file_issues:
                        clean_line = issue["message"].removeprefix("❌ ").removeprefix("⚠️ ")
                        combined_msg += f"\n- {clean_line}"
                    escaped_msg = self._escape(combined_msg)

                print(f"::{level} {file_arg}title={title_val}::{escaped_msg}")

    def _write_summary(self, all_issues: list[GithubIssue]) -> None:
        """Write a Markdown report to the GitHub Step Summary file."""
        summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
        if not summary_file or not all_issues:
            return

        summary_path = pathlib.Path(summary_file)
        try:
            with summary_path.open("a", encoding="utf-8") as f:
                f.write("### 🔄 Ruff-Sync Drift Report\n\n")
                f.write("| Severity | Key | Message | File |\n")
                f.write("| :--- | :--- | :--- | :--- |\n")
                for issue in all_issues:
                    severity = "❌ Error" if issue["level"] == "error" else "⚠️ Warning"
                    key = issue["drift_key"] or "-"
                    clean_msg = issue["message"].removeprefix("❌ ").removeprefix("⚠️ ")
                    file_name = issue["file_path"].name if issue["file_path"] else "pyproject.toml"
                    f.write(f"| {severity} | `{key}` | {clean_msg} | `{file_name}` |\n")
                f.write("\n")
        except OSError:
            LOGGER.exception(f"Failed to write to GITHUB_STEP_SUMMARY: {summary_file}")


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
        data["check_name"] = check_name
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
        data["check_name"] = check_name
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
        """Delegate to logger only; not representable in the Code Quality schema."""
        LOGGER.info(message)

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Delegate to logger only; not included in the structured report."""
        (logger or LOGGER).info(message)

    def success(self, message: str) -> None:
        """Delegate to logger only; not representable in the Code Quality schema."""
        LOGGER.info(message)

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
        # Normalize location.path to be relative to the repo root (no absolute paths).
        if file_path:
            if file_path.is_absolute():
                try:
                    path = str(file_path.relative_to(pathlib.Path.cwd()))
                except ValueError:
                    # If the absolute path is outside the CWD (repo root in CI),
                    # fall back to the filename so GitLab can at least attempt a map.
                    path = file_path.name
            else:
                path = str(file_path)
        else:
            path = "pyproject.toml"

        return {
            "description": description,
            "check_name": check_name,
            "fingerprint": self._make_fingerprint(path, check_name, drift_key),
            "severity": severity,
            "location": {"path": path, "lines": {"begin": 1}},
        }

    @staticmethod
    def _make_fingerprint(path: str, check_name: str, drift_key: str | None) -> str:
        """Return a stable MD5 fingerprint for a Code Quality issue.

        The fingerprint must be deterministic (same inputs → same output on
        every pipeline run) so GitLab can track introduced vs resolved issues.
        Never include timestamps, UUIDs, or any other runtime-variable data.
        """
        # Include check_name to prevent collisions if multiple rules trigger on the same key.
        raw = f"ruff-sync:{check_name}:{path}:{drift_key or ''}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324


class SarifResult(TypedDict, total=False):
    """A single SARIF result (finding)."""

    ruleId: str
    level: Literal["error", "warning", "note"]
    message: dict[str, str]
    locations: list[dict[str, Any]]
    fingerprints: dict[str, str]
    properties: dict[str, str]


class SarifFormatter:
    """SARIF v2.1.0 output formatter.

    Accumulates results during the run and writes a complete SARIF document to
    stdout in ``finalize()``.  The CI job redirects stdout to a file::

        ruff-sync check --output-format sarif > results.sarif

    An empty ``results`` list is emitted when no issues were found.

    Schema: https://json.schemastore.org/sarif-2.1.0.json
    """

    _RULE_ID: Final[str] = "RUFF-SYNC-CONFIG-DRIFT"
    _SCHEMA: Final[str] = "https://json.schemastore.org/sarif-2.1.0.json"
    _SARIF_VERSION: Final[str] = "2.1.0"

    def __init__(self) -> None:
        """Initialise with an empty result list."""
        self._results: list[SarifResult] = []

    # ------------------------------------------------------------------
    # Protocol methods
    # ------------------------------------------------------------------

    def note(self, message: str) -> None:
        """Delegate to logger only; not representable in the SARIF schema."""
        LOGGER.info(message)

    def info(self, message: str, logger: logging.Logger | None = None) -> None:
        """Delegate to logger only; not included in the structured report."""
        (logger or LOGGER).info(message)

    def success(self, message: str) -> None:
        """Delegate to logger only; not representable in the SARIF schema."""
        LOGGER.info(message)

    def error(
        self,
        message: str,
        file_path: pathlib.Path | None = None,
        logger: logging.Logger | None = None,
        check_name: str = _DEFAULT_CHECK_NAME,
        drift_key: str | None = None,
    ) -> None:
        """Accumulate an error-level SARIF result."""
        (logger or LOGGER).error(message)
        self._results.append(
            self._make_result(
                message=message,
                level="error",
                file_path=file_path,
                check_name=check_name,
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
        """Accumulate a warning-level SARIF result."""
        (logger or LOGGER).warning(message)
        self._results.append(
            self._make_result(
                message=message,
                level="warning",
                file_path=file_path,
                check_name=check_name,
                drift_key=drift_key,
            )
        )

    def debug(self, message: str, logger: logging.Logger | None = None) -> None:
        """Delegate to logger only; not included in the structured report."""
        (logger or LOGGER).debug(message)

    def diff(self, diff_text: str) -> None:
        """Ignored by structured formatters — diffs are not representable in SARIF."""

    def finalize(self) -> None:
        """Write the collected results as a SARIF v2.1.0 document to stdout.

        Rules are de-duplicated from the accumulated results so the ``rules``
        list contains one entry per unique ``ruleId`` seen across all findings.
        """
        seen_ids: set[str] = set()
        rules: list[dict[str, Any]] = []
        for result in self._results:
            rule_id = result["ruleId"]
            if rule_id not in seen_ids:
                seen_ids.add(rule_id)
                rules.append(
                    {
                        "id": rule_id,
                        "name": "ConfigDrift",
                        "shortDescription": {
                            "text": "Ruff configuration has drifted from upstream."
                        },
                        "helpUri": "https://github.com/Kilo59/ruff-sync",
                    }
                )
        if not rules:
            # No findings — emit a single placeholder rule so the SARIF document
            # is always schema-valid (a tool with zero rules is still valid, but
            # some consumers require at least one rule entry).
            rules = [
                {
                    "id": self._RULE_ID,
                    "name": "ConfigDrift",
                    "shortDescription": {"text": "Ruff configuration has drifted from upstream."},
                    "helpUri": "https://github.com/Kilo59/ruff-sync",
                }
            ]
        sarif_doc: dict[str, Any] = {
            "version": self._SARIF_VERSION,
            "$schema": self._SCHEMA,
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "ruff-sync",
                            "informationUri": "https://github.com/Kilo59/ruff-sync",
                            "rules": rules,
                        }
                    },
                    "results": self._results,
                }
            ],
        }
        print(json.dumps(sarif_doc, indent=2))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_result(
        self,
        message: str,
        level: Literal["error", "warning", "note"],
        file_path: pathlib.Path | None,
        check_name: str | None = None,
        drift_key: str | None = None,
    ) -> SarifResult:
        """Build a single SARIF result object.

        Args:
            message: Human-readable finding text.
            level: SARIF severity level.
            file_path: Source file the finding belongs to.
            check_name: Machine-readable rule identifier.  When provided a
                granular ``ruleId`` of the form ``check_name:drift_key`` is
                used so code-scanning UIs can group findings per key.
            drift_key: Dotted TOML key that drifted (e.g. ``"lint.select"``).
                Included in ``properties`` and used to derive a stable fingerprint.
        """
        artifact_uri = _path_to_artifact_uri(file_path)

        # Build a granular ruleId so findings for different keys are
        # distinguishable in code-scanning UIs (e.g. GitHub Advanced Security).
        if drift_key is not None and check_name is not None:
            rule_id = f"{check_name}:{drift_key}"
        elif check_name is not None:
            rule_id = check_name
        else:
            rule_id = self._RULE_ID

        result: SarifResult = {
            "ruleId": rule_id,
            "level": level,
            "message": {"text": message},
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": artifact_uri, "uriBaseId": "%SRCROOT%"},
                        "region": {"startLine": 1},
                    }
                }
            ],
        }

        # Populate custom properties for tooling that reads SARIF property bags.
        props: dict[str, str] = {}
        if check_name is not None:
            props["check_name"] = check_name
        if drift_key is not None:
            props["drift_key"] = drift_key
        if props:
            result["properties"] = props

        # Derive a stable fingerprint so consumers can deduplicate across runs.
        # Never include timestamps or UUIDs — only stable, content-derived data.
        fingerprint = self._make_fingerprint(artifact_uri, rule_id, drift_key)
        # Use a custom SARIF fingerprint key to reflect that this is not a line-hash.
        result["fingerprints"] = {"ruff-sync-fingerprint/v1": fingerprint}

        return result

    @staticmethod
    def _make_fingerprint(artifact_uri: str, rule_id: str, drift_key: str | None) -> str:
        """Return a stable MD5 fingerprint for a SARIF result.

        The fingerprint must be deterministic (same inputs → same output on
        every pipeline run) so consumers can track introduced vs resolved
        findings.  Never include timestamps, UUIDs, or any other
        runtime-variable data.
        """
        raw = f"ruff-sync:{rule_id}:{artifact_uri}:{drift_key or ''}"
        return hashlib.md5(raw.encode()).hexdigest()  # noqa: S324


def _path_to_artifact_uri(file_path: pathlib.Path | None) -> str:
    """Convert a file path to a relative URI suitable for SARIF artifactLocation.

    SARIF recommends relative URIs with ``uriBaseId`` rather than absolute
    ``file://`` URIs so results are portable across machines.
    """
    if file_path is None:
        return "pyproject.toml"
    if file_path.is_absolute():
        try:
            return str(file_path.relative_to(pathlib.Path.cwd()))
        except ValueError:
            return file_path.name
    return str(file_path)


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
        case OutputFormat.SARIF:
            return SarifFormatter()
