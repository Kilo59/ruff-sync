from __future__ import annotations

import pathlib
from typing import TYPE_CHECKING

import pytest
import respx
from httpx import URL

import ruff_sync

if TYPE_CHECKING:
    from pyfakefs.fake_filesystem import FakeFilesystem


@pytest.mark.asyncio
async def test_check_in_sync(fs: FakeFilesystem):
    # Setup
    pyproject_content = """
[tool.ruff]
target-version = "py310"

"""
    fs.create_file("pyproject.toml", contents=pyproject_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=pyproject_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 0


@pytest.mark.asyncio
async def test_check_out_of_sync(fs: FakeFilesystem, capsys, configure_logging):
    # Setup
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.err
        assert '-target-version = "py310"' in captured.out
        assert '+target-version = "py311"' in captured.out


@pytest.mark.asyncio
async def test_check_pre_commit_out_of_sync(fs: FakeFilesystem, caplog):
    # Setup
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    # Mock uv.lock and .pre-commit-config.yaml to be out of sync
    fs.create_file("uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.0
    hooks:
      - id: ruff
"""
    fs.create_file(".pre-commit-config.yaml", contents=config_content)

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=local_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            pre_commit=True,
        )

        # Ruff config matches completely, but pre_commit is out of sync -> Exit code 3
        exit_code = await ruff_sync.check(args)
        assert exit_code == 3

        assert "pre-commit Ruff hook is out of sync" in caplog.text


@pytest.mark.asyncio
async def test_check_semantic_sync(fs: FakeFilesystem):
    # A local comment does NOT make you out of sync — ruff-sync only adds/updates
    # keys, it never strips local-only additions like comments.
    local_content = """
[tool.ruff]
# Some local comment
target-version = "py310"
line-length = 90
"""
    upstream_content = """
[tool.ruff]
target-version = "py310"
line-length = 90
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        # Strict check: merging upstream produces no text change → in sync
        args_strict = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )
        assert await ruff_sync.check(args_strict) == 0

        # Semantic check also passes — values are identical
        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 0


@pytest.mark.asyncio
async def test_check_semantic_out_of_sync(fs: FakeFilesystem):
    # Setup - actual values differ
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 1


@pytest.mark.asyncio
async def test_check_semantic_diff_output(fs: FakeFilesystem, capsys, configure_logging):
    # Setup - actual values differ
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args_semantic = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=True,
            diff=True,
        )
        assert await ruff_sync.check(args_semantic) == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.err
        assert "--- local (semantic)" in captured.out
        assert "+++ upstream (semantic)" in captured.out
        # Check for JSON-style diff content
        assert '-  "target-version": "py310"' in captured.out
        assert '+  "target-version": "py311"' in captured.out


@pytest.mark.asyncio
async def test_check_multi_upstream(fs: FakeFilesystem, capsys, configure_logging):
    """Check supports multiple upstreams and bases status on the fully merged result."""
    # Setup
    local_content = """
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F"]
"""
    upstream1_content = """
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E"]
"""
    upstream2_content = """
[tool.ruff]
line-length = 100

[tool.ruff.lint]
select = ["E", "F"]
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    u1_url = URL("https://example.com/u1/pyproject.toml")
    u2_url = URL("https://example.com/u2/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/u1/pyproject.toml").respond(200, content=upstream1_content)
        respx_mock.get("/u2/pyproject.toml").respond(200, content=upstream2_content)

        args = ruff_sync.Arguments(
            command="check",
            upstream=(u1_url, u2_url),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
        )

        # 1. Fully merged config matches local -> success
        assert await ruff_sync.check(args) == 0

        # 2. Local config deviates from the *merged* result -> failure
        # (e.g. local matches only upstream1, but upstream2 should have overridden it)
        source_path.write_text(upstream1_content)
        assert await ruff_sync.check(args) == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.err
        assert "+line-length = 100" in captured.out
        assert '+select = ["E", "F"]' in captured.out


@pytest.mark.asyncio
async def test_check_both_out_of_sync_prioritizes_config_drift(
    fs: FakeFilesystem, capsys, configure_logging
):
    """Verify that Exit 1 is returned when both ruff config AND pre-commit are out of sync."""
    # Setup - ruff config drift
    local_content = '[tool.ruff]\ntarget-version = "py310"\n'
    upstream_content = '[tool.ruff]\ntarget-version = "py311"\n'
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    # Mock uv.lock and .pre-commit-config.yaml to be out of sync (Hook Drift)
    fs.create_file("uv.lock", contents='[[package]]\nname = "ruff"\nversion = "0.15.0"')
    config_content = """repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.0
"""
    fs.create_file(".pre-commit-config.yaml", contents=config_content)

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(200, content=upstream_content)

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            pre_commit=True,
        )

        # Both out of sync -> Exit code 1 (config drift takes priority)
        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        assert "is out of sync!" in captured.err
        assert '-target-version = "py310"' in captured.out
        assert '+target-version = "py311"' in captured.out
        # Pre-commit drift should NOT be reported if config drift was found and resulted in exit 1
        assert "⚠️ Pre-commit hook version is out of sync!" not in captured.out


@pytest.mark.asyncio
async def test_check_out_of_sync_json_format(fs: FakeFilesystem, capsys, configure_logging):
    # Setup mirrors the default-format test but uses JSON output_format
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            output_format=ruff_sync.constants.OutputFormat.JSON,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()

        # JSON formatter should emit valid JSON records (one per line).
        import json

        # Logs go to stderr, but structured output (notes) might go elsewhere.
        # In our implementation, JsonFormatter prints to stdout.
        # We filter for lines starting with '{' to avoid parsing plain-text diffs.
        combined_output = captured.out + captured.err
        json_lines = [line for line in combined_output.splitlines() if line.strip().startswith("{")]
        assert json_lines, "Expected at least one JSON log line for out-of-sync config"

        records = [json.loads(line) for line in json_lines]

        # There should be at least one error record describing the out-of-sync state.
        error_records = [r for r in records if r.get("level") == "error"]
        assert error_records, "Expected at least one error record in JSON output"

        error_messages = " ".join(r.get("message", "") for r in error_records)
        assert "is out of sync" in error_messages

        # When file_path is set, JSON output should include a file field.
        files = {r.get("file") for r in records if "file" in r}
        assert "pyproject.toml" in files


@pytest.mark.asyncio
async def test_check_out_of_sync_github_format(fs: FakeFilesystem, capsys, configure_logging):
    # Setup mirrors the default-format test but uses GITHUB output_format
    local_content = """
[tool.ruff]
target-version = "py310"
"""
    upstream_content = """
[tool.ruff]
target-version = "py311"
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            output_format=ruff_sync.constants.OutputFormat.GITHUB,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()

        # GitHub formatter should emit ::error / ::warning annotations.
        # Combined output because we delegate standard output to a logger (stderr)
        # while workflow commands go to stdout.
        combined_output = captured.out + captured.err
        error_lines = [line for line in combined_output.splitlines() if line.startswith("::error")]
        assert error_lines, "Expected at least one ::error line in GitHub output"

        # Ensure the annotation references the config file as a relative path.
        assert any("file=pyproject.toml" in line for line in error_lines)

        # Also ensure the human-readable message is present after the annotation.
        assert any("is out of sync" in line for line in error_lines)


@pytest.mark.asyncio
async def test_check_in_sync_json_format(
    fs: FakeFilesystem,
    capsys,
    configure_logging,
):
    """Ensure JSON formatter reports success and no errors when configs are in sync."""
    local_content = """
[tool.ruff]
target-version = "py311"
line-length = 88
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")
    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=local_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            output_format=ruff_sync.constants.OutputFormat.JSON,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        combined_output = captured.out + captured.err
        json_lines = [line for line in combined_output.splitlines() if line.strip().startswith("{")]
        assert json_lines, "Expected at least one JSON record in output"

        import json

        records = [json.loads(line) for line in json_lines]

        # No error-level records
        assert all(r.get("level") != "error" for r in records)

        # At least one success/in-sync record
        assert any(
            r.get("level") in ("success", "info") and "in sync" in (r.get("message") or "").lower()
            for r in records
        )


@pytest.mark.asyncio
async def test_check_in_sync_github_format(
    fs: FakeFilesystem,
    capsys,
    configure_logging,
):
    """Ensure GitHub formatter does not emit ::error lines when configs are in sync."""
    local_content = """
[tool.ruff]
target-version = "py311"
line-length = 88
"""
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")
    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=local_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=True,
            output_format=ruff_sync.constants.OutputFormat.GITHUB,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        combined_output = captured.out + captured.err

        # No GitHub ::error annotations should be emitted
        assert "::error" not in combined_output

        # Human-friendly success/note message should still be present
        assert "in sync" in combined_output.lower()
        assert "ruff" in combined_output.lower()


@pytest.mark.asyncio
async def test_check_upstream_error_returns_4(fs: FakeFilesystem, capsys):
    """Verify that an unreachable upstream URL causes check() to raise UpstreamError.

    The CLI catches UpstreamError and returns exit code 4.  Here we test check()
    directly — it propagates UpstreamError so the CLI can handle it uniformly.
    """
    from ruff_sync.core import UpstreamError

    local_content = '[tool.ruff]\ntarget-version = "py310"\n'
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(404)

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=False,
        )

        with pytest.raises(UpstreamError):
            await ruff_sync.check(args)


@pytest.mark.asyncio
async def test_check_sarif_format(fs: FakeFilesystem, capsys, configure_logging):
    """Verify --output-format sarif produces a valid SARIF v2.1.0 document."""
    import json

    local_content = '[tool.ruff]\ntarget-version = "py310"\n'
    upstream_content = '[tool.ruff]\ntarget-version = "py311"\n'
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=False,
            output_format=ruff_sync.constants.OutputFormat.SARIF,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        # SARIF is written as a single JSON document to stdout
        sarif_doc = json.loads(captured.out)

        # Structural assertions — must be a valid SARIF v2.1.0 document
        assert sarif_doc["version"] == "2.1.0"
        assert "runs" in sarif_doc
        assert len(sarif_doc["runs"]) == 1

        run = sarif_doc["runs"][0]
        assert run["tool"]["driver"]["name"] == "ruff-sync"
        rules = run["tool"]["driver"]["rules"]
        assert len(rules) >= 1
        # Rules are now de-duplicated and keyed per drifted TOML path.
        # Each ruleId includes the check_name and the drift_key so code-scanning
        # UIs can group findings per key across runs.
        rule_ids = {r["id"] for r in rules}
        # The drifted key 'target-version' should show up in at least one rule ID.
        assert any("target-version" in rid for rid in rule_ids), (
            f"Expected a per-key ruleId containing 'target-version', got: {rule_ids}"
        )

        # Semantic assertions — at least one result must reference the drifted key
        results = run["results"]
        assert results, "Expected at least one SARIF result for out-of-sync config"

        error_results = [r for r in results if r["level"] == "error"]
        assert error_results, "Expected at least one error-level SARIF result"

        # Each result must have a message and a physical location
        for result in error_results:
            assert "text" in result["message"]
            loc = result["locations"][0]["physicalLocation"]
            assert "artifactLocation" in loc
            assert loc["region"]["startLine"] == 1
            # Each result must carry stable fingerprints and custom properties.
            assert "fingerprints" in result, "Expected 'fingerprints' on each SARIF result"
            assert "properties" in result, "Expected 'properties' on each SARIF result"
            assert "drift_key" in result["properties"], "Expected 'drift_key' in result properties"
            assert "check_name" in result["properties"], (
                "Expected 'check_name' in result properties"
            )

        # The drifted key should appear in at least one message
        all_messages = " ".join(r["message"]["text"] for r in results)
        assert "target-version" in all_messages


@pytest.mark.asyncio
async def test_check_sarif_format_in_sync(fs: FakeFilesystem, capsys, configure_logging):
    """Verify SARIF formatter emits zero results when configs are in sync."""
    import json

    local_content = '[tool.ruff]\ntarget-version = "py311"\n'
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=local_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=False,
            output_format=ruff_sync.constants.OutputFormat.SARIF,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 0

        captured = capsys.readouterr()
        sarif_doc = json.loads(captured.out)

        assert sarif_doc["version"] == "2.1.0"
        results = sarif_doc["runs"][0]["results"]
        assert results == [], f"Expected empty results for in-sync config, got {results}"


@pytest.mark.asyncio
async def test_check_sarif_multiple_drifts(fs: FakeFilesystem, capsys, configure_logging):
    """Verify SARIF output includes multiple results for multiple drifted keys."""
    import json

    local_content = '[tool.ruff]\ntarget-version = "py310"\nline-length = 100\n'
    upstream_content = '[tool.ruff]\ntarget-version = "py311"\nline-length = 88\n'
    fs.create_file("pyproject.toml", contents=local_content)
    source_path = pathlib.Path("pyproject.toml")

    upstream_url = URL("https://example.com/pyproject.toml")

    with respx.mock(base_url="https://example.com") as respx_mock:
        respx_mock.get("/pyproject.toml").respond(
            200,
            content_type="text/plain",
            content=upstream_content,
        )

        args = ruff_sync.Arguments(
            command="check",
            upstream=(upstream_url,),
            to=source_path,
            exclude=set(),
            verbose=0,
            semantic=False,
            diff=False,
            output_format=ruff_sync.constants.OutputFormat.SARIF,
        )

        exit_code = await ruff_sync.check(args)
        assert exit_code == 1

        captured = capsys.readouterr()
        sarif_doc = json.loads(captured.out)

        results = sarif_doc["runs"][0]["results"]
        # Should have at least two results (one for target-version, one for line-length)
        assert len(results) >= 2

        drift_keys = {r["properties"]["drift_key"] for r in results if "properties" in r}
        assert "target-version" in drift_keys
        assert "line-length" in drift_keys

        rule_ids = {r["ruleId"] for r in results}
        assert any("target-version" in rid for rid in rule_ids)
        assert any("line-length" in rid for rid in rule_ids)

        # Check for custom fingerprint key
        for result in results:
            assert "ruff-sync-fingerprint/v1" in result.get("fingerprints", {})


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
