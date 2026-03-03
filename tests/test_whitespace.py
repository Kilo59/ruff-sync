from __future__ import annotations

import pytest
import tomlkit

import ruff_sync


def test_merge_preserves_whitespace():
    """
    Test that merging ruff config into a TOML document preserves existing whitespace.
    Reproduction for Issue #6.
    """
    source_toml_s = """[tool.poetry]
name = "test-project"

[tool.ruff]
target-version = "py310"
line-length = 120
# There should be exactly one blank line after this comment

[tool.coverage.run]
include = ["foo.py"]
"""

    upstream_ruff_s = """[tool.ruff]
target-version = "py310"
line-length = 120
lint.select = ["F", "E"]
"""

    source_doc = tomlkit.parse(source_toml_s)
    upstream_doc = tomlkit.parse(upstream_ruff_s)
    upstream_ruff = upstream_doc["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    # Check if we still have the comment and the following blank line
    assert "# There should be exactly one blank line after this comment" in merged_s
    # The current implementation might be adding extra newlines or removing them
    # We want to ensure 'line-length = 120\n# ...' is preserved and not mangled

    print(f"Merged TOML:\n{merged_s}")

    # In Issue #6, the user noted "1 too many newlines" or "remove too much whitespace"
    # Let's check for double newlines that shouldn't be there
    assert "\n\n\n[" not in merged_s, "Found triple newlines, expected at most double"


def test_merge_nested_table_whitespace():
    """
    Test that merging nested tables (like per-file-ignores) preserves whitespace.
    """
    source_toml_s = """[tool.ruff]
lint.select = ["F"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]

[tool.other]
key = "value"
"""

    upstream_ruff_s = """[tool.ruff]
lint.select = ["F", "E"]
lint.per-file-ignores = {"__init__.py" = ["F401", "F403"]}
"""

    source_doc = tomlkit.parse(source_toml_s)
    upstream_ruff = tomlkit.parse(upstream_ruff_s)["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    print(f"Merged Nested TOML:\n{merged_s}")
    # Ensure there's a newline between the end of ruff config and the next table
    assert "]\n[tool.other]" in merged_s or "]\n\n[tool.other]" in merged_s


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
