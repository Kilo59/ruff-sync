from __future__ import annotations

import json
import logging
import pathlib
from typing import TYPE_CHECKING, Any

import pytest

from ruff_sync.constants import MISSING, OutputFormat
from ruff_sync.formatters import (
    GithubFormatter,
    GitlabFormatter,
    JsonFormatter,
    TextFormatter,
    get_formatter,
)

if TYPE_CHECKING:
    from ruff_sync.formatters import ResultFormatter

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(params=[TextFormatter, GithubFormatter, JsonFormatter])
def formatter(request: pytest.FixtureRequest) -> ResultFormatter:
    """Fixture providing instances of all streaming formatters."""
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

    def test_finalize_is_noop_for_streaming_formatters(
        self,
        formatter: ResultFormatter,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """finalize() must not emit any output for streaming formatters."""
        formatter.finalize()
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

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

        # Call the method with all possible extras (only error/warning take file_path and drift_key)
        kwargs: dict[str, Any] = {"logger": logger}
        if method in ("error", "warning"):
            kwargs["file_path"] = file_path
            kwargs["drift_key"] = "lint.select"
            kwargs["check_name"] = "custom-check"

        getattr(fmt, method)("msg", **kwargs)

        data = json.loads(capsys.readouterr().out)
        assert data["logger"] == "custom"
        if method in ("error", "warning"):
            assert data["file"] == "f.py"
            assert data["drift_key"] == "lint.select"
            assert data["check_name"] == "custom-check"


class TestGitlabFormatter:
    """Tests for GitlabFormatter (GitLab Code Quality report format)."""

    def test_default_path_when_file_path_is_none(self, capsys: pytest.CaptureFixture[str]) -> None:
        """When file_path is None, GitlabFormatter should default to 'pyproject.toml'."""
        fmt = GitlabFormatter()
        fmt.error("drift", file_path=None)
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert len(issues) == 1
        assert issues[0]["location"]["path"] == "pyproject.toml"

    def test_absolute_path_normalization(self, capsys: pytest.CaptureFixture[str]) -> None:
        """GitlabFormatter must normalize absolute paths to be relative to CWD."""
        fmt = GitlabFormatter()
        cwd = pathlib.Path.cwd()
        abs_path = cwd / "subdir" / "pyproject.toml"

        fmt.error("drift", file_path=abs_path)
        fmt.finalize()

        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["location"]["path"] == "subdir/pyproject.toml"

    def test_finalize_empty_produces_empty_array(self, capsys: pytest.CaptureFixture[str]) -> None:
        """An empty formatter must emit [] — the GitLab 'no issues' signal."""
        fmt = GitlabFormatter()
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues == []

    def test_error_produces_major_severity(self, capsys: pytest.CaptureFixture[str]) -> None:
        """error() must accumulate a major-severity issue."""
        fmt = GitlabFormatter()
        fmt.error("drift found", file_path=pathlib.Path("pyproject.toml"))
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert len(issues) == 1
        assert issues[0]["severity"] == "major"
        assert issues[0]["location"]["path"] == "pyproject.toml"
        assert issues[0]["location"]["lines"]["begin"] == 1
        assert "fingerprint" in issues[0]
        assert "description" in issues[0]
        assert issues[0]["check_name"] == "ruff-sync/config-drift"

    def test_warning_produces_minor_severity(self, capsys: pytest.CaptureFixture[str]) -> None:
        """warning() must accumulate a minor-severity issue."""
        fmt = GitlabFormatter()
        fmt.warning("stale hook", file_path=pathlib.Path(".pre-commit-config.yaml"))
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert len(issues) == 1
        assert issues[0]["severity"] == "minor"

    def test_custom_check_name_is_preserved(self, capsys: pytest.CaptureFixture[str]) -> None:
        """A caller-supplied check_name must appear in the issue object."""
        fmt = GitlabFormatter()
        fmt.error("hook stale", check_name="ruff-sync/precommit-stale")
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["check_name"] == "ruff-sync/precommit-stale"

    def test_drift_key_produces_distinct_fingerprints(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Different drift_key values must yield different fingerprints."""
        fmt = GitlabFormatter()
        fmt.error("drift", file_path=pathlib.Path("pyproject.toml"), drift_key="lint.select")
        fmt.error("drift", file_path=pathlib.Path("pyproject.toml"), drift_key="target-version")
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["fingerprint"] != issues[1]["fingerprint"]

    def test_fingerprint_is_stable(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Same inputs must produce the same fingerprint across multiple instances."""
        fmt1 = GitlabFormatter()
        fmt2 = GitlabFormatter()
        fp = pathlib.Path("pyproject.toml")
        fmt1.error("drift found", file_path=fp, drift_key="lint.select")
        fmt2.error("drift found", file_path=fp, drift_key="lint.select")
        fmt1.finalize()
        fp1 = json.loads(capsys.readouterr().out)[0]["fingerprint"]
        fmt2.finalize()
        fp2 = json.loads(capsys.readouterr().out)[0]["fingerprint"]
        assert fp1 == fp2

    def test_absolute_path_outside_cwd_normalization(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """If an absolute path is outside CWD, it must fall back to the filename."""
        fmt = GitlabFormatter()
        # Use a path that is guaranteed to be outside the project root/CWD
        outside_path = pathlib.Path("/external.toml")

        fmt.error("drift", file_path=outside_path)
        fmt.finalize()

        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["location"]["path"] == "external.toml"

    def test_fingerprint_includes_check_name(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Different check_names on the same file/key must produce distinct fingerprints."""
        fmt = GitlabFormatter()
        path = pathlib.Path("pyproject.toml")

        fmt.error("drift", file_path=path, drift_key="lint.select", check_name="rule-1")
        fmt.error("drift", file_path=path, drift_key="lint.select", check_name="rule-2")
        fmt.finalize()

        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["fingerprint"] != issues[1]["fingerprint"]

    def test_distinct_fingerprints_no_drift_key(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Omitting drift_key must still produce stable and distinct fingerprints."""
        fmt1 = GitlabFormatter()
        fmt2 = GitlabFormatter()
        path1 = pathlib.Path("pyproject.toml")
        path2 = pathlib.Path("ruff.toml")

        # Stable for same path
        fmt1.error("drift", file_path=path1, drift_key=None)
        fmt2.error("drift", file_path=path1, drift_key=None)
        fmt1.finalize()
        fp1_a = json.loads(capsys.readouterr().out)[0]["fingerprint"]
        fmt2.finalize()
        fp1_b = json.loads(capsys.readouterr().out)[0]["fingerprint"]
        assert fp1_a == fp1_b

        # Distinct for different paths
        fmt1 = GitlabFormatter()
        fmt1.error("drift", file_path=path1, drift_key=None)
        fmt1.error("drift", file_path=path2, drift_key=None)
        fmt1.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues[0]["fingerprint"] != issues[1]["fingerprint"]

    def test_no_bom_in_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Output must not start with a UTF-8 BOM (GitLab rejects BOM-prefixed JSON)."""
        fmt = GitlabFormatter()
        fmt.finalize()
        assert not capsys.readouterr().out.startswith("\ufeff")

    def test_multiple_issues_accumulated(self, capsys: pytest.CaptureFixture[str]) -> None:
        """All error() and warning() calls must appear in the final JSON array."""
        fmt = GitlabFormatter()
        fmt.error("error one", file_path=pathlib.Path("pyproject.toml"), drift_key="lint.select")
        fmt.warning(
            "warn one",
            file_path=pathlib.Path("pyproject.toml"),
            drift_key="target-version",
        )
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert len(issues) == 2
        assert issues[0]["severity"] == "major"
        assert issues[1]["severity"] == "minor"

    def test_note_and_success_do_not_produce_issues(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """note() and success() must not populate the issue list."""
        fmt = GitlabFormatter()
        fmt.note("checking...")
        fmt.success("✅ in sync")
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues == []

    def test_diff_is_ignored(self, capsys: pytest.CaptureFixture[str]) -> None:
        """diff() must not add any issue to the report."""
        fmt = GitlabFormatter()
        fmt.diff("--- a\n+++ b\n@@ ...")
        fmt.finalize()
        issues = json.loads(capsys.readouterr().out)
        assert issues == []

    def test_diagnostic_methods_delegate_to_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify diagnostic methods (info, debug, note, success) delegate to the logger."""
        fmt = GitlabFormatter()

        # note/success/info log at INFO level
        with caplog.at_level(logging.INFO, logger="ruff_sync.formatters"):
            fmt.note("note msg")
            fmt.success("success msg")
            fmt.info("info msg")

        # debug logs at DEBUG level
        with caplog.at_level(logging.DEBUG, logger="ruff_sync.formatters"):
            fmt.debug("debug msg")

        assert "note msg" in caplog.text
        assert "success msg" in caplog.text
        assert "info msg" in caplog.text
        assert "debug msg" in caplog.text

    def test_custom_logger_delegation(self) -> None:
        """Verify diagnostic methods delegate to a custom logger if provided."""
        fmt = GitlabFormatter()

        class LoggerSpy:
            def __init__(self) -> None:
                self.info_called = False
                self.debug_called = False

            def info(self, msg: str) -> None:
                self.info_called = True

            def debug(self, msg: str) -> None:
                self.debug_called = True

        mock_logger = LoggerSpy()

        fmt.info("info msg", logger=mock_logger)  # type: ignore[arg-type]
        assert mock_logger.info_called

        fmt.debug("debug msg", logger=mock_logger)  # type: ignore[arg-type]
        assert mock_logger.debug_called


class TestJsonFormatterMetadata:
    """Verify metadata propagation in JsonFormatter."""

    def test_json_formatter_always_includes_check_name(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JsonFormatter must always include check_name, even if it is the default."""
        from ruff_sync.formatters import JsonFormatter

        fmt = JsonFormatter()
        fmt.error("drift")
        data = json.loads(capsys.readouterr().out)
        assert data["check_name"] == "ruff-sync/config-drift"

        fmt.warning("stale")
        data = json.loads(capsys.readouterr().out)
        assert data["check_name"] == "ruff-sync/config-drift"


class SpyFormatter:
    """A minimal ResultFormatter that tracks calls to ensure they occur."""

    def __init__(self) -> None:
        """Initialize the spy with state tracking fields."""
        self.finalized = False
        self.errors: list[str] = []

    def note(self, message: str) -> None:
        """No-op note implementation."""

    def info(self, message: str, logger: Any = None) -> None:
        """No-op info implementation."""

    def success(self, message: str) -> None:
        """No-op success implementation."""

    def debug(self, message: str, logger: Any = None) -> None:
        """No-op debug implementation."""

    def diff(self, diff_text: str) -> None:
        """No-op diff implementation."""

    def error(
        self,
        message: str,
        file_path: Any = None,
        logger: Any = None,
        check_name: str = "ruff-sync/config-drift",
        drift_key: str | None = None,
    ) -> None:
        """Record the error message."""
        self.errors.append(message)

    def warning(
        self,
        message: str,
        file_path: Any = None,
        logger: Any = None,
        check_name: str = "ruff-sync/config-drift",
        drift_key: str | None = None,
    ) -> None:
        """No-op warning implementation."""

    def finalize(self) -> None:
        """Flush the accumulated report and finish the sync process."""
        self.finalized = True


class TestCLILifecycle:
    """Verify that core.py ensures the formatter lifecycle (finalize) is honored."""

    @pytest.mark.asyncio
    async def test_check_calls_finalize_on_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """check() must call finalize() even when everything is in sync."""
        from ruff_sync import core

        spy = SpyFormatter()
        monkeypatch.setattr(core, "get_formatter", lambda _: spy)

        # Mock dependencies to avoid real IO
        monkeypatch.setattr(pathlib.Path, "exists", lambda _: True)
        # Mock TOMLFile.read to return a valid sync config
        from tomlkit import parse

        content = parse("[tool.ruff]\nline-length = 80")
        monkeypatch.setattr("ruff_sync.core.TOMLFile.read", lambda _: content)

        async def _mock_merge(*args, **kwargs):
            return content

        monkeypatch.setattr("ruff_sync.core._merge_multiple_upstreams", _mock_merge)

        from httpx import URL

        from ruff_sync.cli import Arguments

        args = Arguments(
            command="check",
            upstream=(URL("https://example.com"),),
            to=pathlib.Path("pyproject.toml"),
            exclude=MISSING,
            verbose=0,
            output_format=OutputFormat.TEXT,
        )

        await core.check(args)
        assert spy.finalized

    @pytest.mark.asyncio
    async def test_check_calls_finalize_on_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """check() must call finalize() even when an exception occurs."""
        from ruff_sync import core

        spy = SpyFormatter()
        monkeypatch.setattr(core, "get_formatter", lambda _: spy)

        # Force an early return/error by making the file not exist
        monkeypatch.setattr(pathlib.Path, "exists", lambda _: False)

        from httpx import URL

        from ruff_sync.cli import Arguments

        args = Arguments(
            command="check",
            upstream=(URL("https://example.com"),),
            to=pathlib.Path("nonexistent.toml"),
            exclude=MISSING,
            verbose=0,
            output_format=OutputFormat.TEXT,
        )

        await core.check(args)
        assert len(spy.errors) > 0
        assert spy.finalized


def test_get_formatter_factory() -> None:
    """Verify get_formatter returns correct types for all OutputFormat values."""
    assert isinstance(get_formatter(OutputFormat.TEXT), TextFormatter)
    assert isinstance(get_formatter(OutputFormat.JSON), JsonFormatter)
    assert isinstance(get_formatter(OutputFormat.GITHUB), GithubFormatter)
    assert isinstance(get_formatter(OutputFormat.GITLAB), GitlabFormatter)


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
