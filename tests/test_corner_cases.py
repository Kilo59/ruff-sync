from __future__ import annotations

from typing import Any, cast

import pytest
import tomlkit

import ruff_sync


def test_merge_dotted_keys_with_new_subtable():
    """
    Test merging into a table that uses dotted keys when adding a new sub-table.
    This handles the case where [tool.ruff] has lint.select, and we add
    [tool.ruff.lint.per-file-ignores].
    """
    source_s = """[tool.ruff]
target-version = "py38"
lint.select = ["F"]
"""
    # Note: we want the result to ideally stay clean.
    # If the upstream has a full table header, we might want to respect that
    # or keep it as a dotted key if it's simple.
    upstream_s = """[tool.ruff]
target-version = "py310"
lint.select = ["F", "E"]
[tool.ruff.lint.per-file-ignores]
"x.py" = ["F401"]
"""

    source_doc = tomlkit.parse(source_s)
    upstream_ruff = cast("Any", tomlkit.parse(upstream_s))["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    print(f"Merged Result:\n{merged_s}")

    merged_data = tomlkit.parse(merged_s)
    ruff = cast("Any", merged_data)["tool"]["ruff"]

    assert ruff["target-version"] == "py310"
    assert ruff["lint"]["select"] == ["F", "E"]
    assert ruff["lint"]["per-file-ignores"] == {"x.py": ["F401"]}

    # Check structure: it shouldn't have doubled tool.ruff or broken headers
    assert "[lint.per-file-ignores]" not in merged_s, (
        "Should have tool.ruff prefix or be dotted"
    )
    assert (
        "[tool.ruff.lint.per-file-ignores]" in merged_s
    ) or "lint.per-file-ignores =" in merged_s


def test_merge_preserves_comments_with_dotted_keys():
    source_s = """[tool.ruff]
# Target version comment
target-version = "py38"
lint.select = ["F"] # lint comment
"""
    upstream_s = """[tool.ruff]
target-version = "py310"
lint.select = ["E"]
"""
    source_doc = tomlkit.parse(source_s)
    upstream_ruff = cast("Any", tomlkit.parse(upstream_s))["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    assert "# Target version comment" in merged_s
    assert "# lint comment" in merged_s
    assert 'target-version = "py310"' in merged_s


if __name__ == "__main__":
    pytest.main([__file__, "-vv", "-s"])
