"""Tests for the system module."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from ruff_sync.system import (
    compute_effective_rules,
    get_all_ruff_rules,
    get_ruff_config_markdown,
    get_ruff_linters,
    get_ruff_rule_markdown,
)
from ruff_sync.types_ import RuffRule


class FakeProcess:
    """Fake asyncio subprocess for testing without unittest.mock."""

    def __init__(
        self,
        stdout: bytes = b"",
        stderr: bytes = b"",
        returncode: int = 0,
    ) -> None:
        """Initialize FakeProcess with stdout, stderr, and returncode."""
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode

    async def communicate(self) -> tuple[bytes, bytes]:
        """Simulate process communication by returning buffered stdout and stderr."""
        return self._stdout, self._stderr


class SubprocessSpy:
    """Spy for asyncio.create_subprocess_exec calls."""

    def __init__(
        self,
        fake_process: FakeProcess | None = None,
        side_effect: Exception | None = None,
    ) -> None:
        """Initialize SubprocessSpy with an optional fake process or side effect exception."""
        self.called_args: list[tuple[Any, ...]] = []
        self.called_kwargs: list[dict[str, Any]] = []
        self.fake_process = fake_process or FakeProcess()
        self.side_effect = side_effect

    async def __call__(self, *args: Any, **kwargs: Any) -> FakeProcess:
        """Record invocation arguments and return the fake process or raise side effect."""
        self.called_args.append(args)
        self.called_kwargs.append(kwargs)
        if self.side_effect is not None:
            raise self.side_effect
        return self.fake_process


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_success(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = SubprocessSpy(FakeProcess(stdout=b"RUF012 rule docs", returncode=0))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_rule_markdown("RUF012")
    assert result == "RUF012 rule docs"
    assert len(spy.called_args) == 1
    assert spy.called_args[0] == ("ruff", "rule", "RUF012")
    assert spy.called_kwargs[0] == {
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_by_name(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = SubprocessSpy(FakeProcess(stdout=b"unused-imports rule docs", returncode=0))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_rule_markdown("unused-imports")
    assert result == "unused-imports rule docs"
    assert len(spy.called_args) == 1
    assert spy.called_args[0] == ("ruff", "rule", "unused-imports")
    assert spy.called_kwargs[0] == {
        "stdout": asyncio.subprocess.PIPE,
        "stderr": asyncio.subprocess.PIPE,
    }


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_error_code(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = SubprocessSpy(FakeProcess(stderr=b"Rule not found", returncode=1))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_rule_markdown("NONEXISTENT")
    assert result is None


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = SubprocessSpy(side_effect=FileNotFoundError())
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_rule_markdown("RUF012")
    assert result is None


@pytest.mark.asyncio
async def test_get_ruff_rule_markdown_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    # Test that the generic Exception catch logs and returns None
    spy = SubprocessSpy(side_effect=RuntimeError("Unexpected error"))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_rule_markdown("RUF012")
    assert result is None


@pytest.mark.asyncio
async def test_get_ruff_config_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = SubprocessSpy(FakeProcess(stdout=b"lint.select docs", returncode=0))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    result = await get_ruff_config_markdown("tool.ruff.lint.select")
    assert result == "lint.select docs"
    assert spy.called_args[0] == ("ruff", "config", "lint.select")

    assert await get_ruff_config_markdown("tool.ruff") is None


@pytest.mark.asyncio
async def test_get_all_ruff_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    rules_json = b'[{"code": "RUF012", "name": "mutable-class-default"}]'
    spy = SubprocessSpy(FakeProcess(stdout=rules_json, returncode=0))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    rules = await get_all_ruff_rules()
    assert len(rules) == 1
    assert rules[0]["code"] == "RUF012"


@pytest.mark.asyncio
async def test_get_ruff_linters(monkeypatch: pytest.MonkeyPatch) -> None:
    linters_json = b'[{"name": "pyflakes", "prefix": "F"}]'
    spy = SubprocessSpy(FakeProcess(stdout=linters_json, returncode=0))
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spy)

    linters = await get_ruff_linters()
    assert len(linters) == 1
    assert linters[0]["name"] == "pyflakes"


def test_compute_effective_rules() -> None:
    """Verify that compute_effective_rules computes Enabled, Ignored, and Disabled statuses."""
    all_rules: list[RuffRule] = [
        {
            "code": "RUF012",
            "name": "mutable-class-default",
            "linter": "ruff",
            "summary": "Mutable class default",
        },
        {
            "code": "F401",
            "name": "unused-import",
            "linter": "pyflakes",
            "summary": "Unused import",
        },
        {
            "code": "E501",
            "name": "line-too-long",
            "linter": "pycodestyle",
            "summary": "Line too long",
        },
    ]
    config = {
        "tool": {
            "ruff": {
                "lint": {
                    "select": ["RUF"],
                    "ignore": ["RUF012"],
                }
            }
        }
    }
    effective = compute_effective_rules(all_rules, config)
    statuses = {r["code"]: r.get("status") for r in effective}
    assert statuses["RUF012"] == "Ignored"
    assert statuses["F401"] == "Disabled"


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
