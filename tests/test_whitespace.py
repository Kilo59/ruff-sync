from __future__ import annotations

from typing import Any, cast

import pytest
import tomlkit

import ruff_sync


def test_merge_preserves_whitespace():
    """
    Test that merging ruff config into a TOML document preserves existing whitespace
    and correctly merges the configuration.
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
    upstream_ruff = cast("Any", upstream_doc)["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    # Check if we still have the comment and the following blank line
    assert "# There should be exactly one blank line after this comment" in merged_s
    # The current implementation might be adding extra newlines or removing them
    # We want to ensure 'line-length = 120\n# ...' is preserved and not mangled

    print(f"Merged TOML:\n{merged_s}")

    # Semantics: check merged values
    merged_data = tomlkit.parse(merged_s)
    merged_ruff = cast("Any", merged_data)["tool"]["ruff"]
    assert merged_ruff["target-version"] == "py310"
    assert merged_ruff["line-length"] == 120
    assert list(merged_ruff["lint"]["select"]) == ["F", "E"]

    # In Issue #6, the user noted "1 too many newlines" or "remove too much whitespace"
    # Let's check for double newlines that shouldn't be there
    assert "\n\n\n[" not in merged_s, "Found triple newlines, expected at most double"


def test_merge_nested_table_whitespace():
    """
    Test that merging nested tables (like per-file-ignores) preserves whitespace
    and correctly merges the nested configuration content.
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
    upstream_ruff = cast("Any", tomlkit.parse(upstream_ruff_s))["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    print(f"Merged Nested TOML:\n{merged_s}")
    # Ensure there's a newline between the end of ruff config and the next table
    assert "]\n[tool.other]" in merged_s or "]\n\n[tool.other]" in merged_s

    # Validate merged configuration content
    merged_data = tomlkit.parse(merged_s)
    merged_ruff = cast("Any", merged_data)["tool"]["ruff"]

    # lint.select should include the updated values from upstream
    assert list(merged_ruff["lint"]["select"]) == ["F", "E"]

    # per-file-ignores for __init__.py should reflect the merged/updated values
    per_file_ignores = merged_ruff["lint"]["per-file-ignores"]
    assert "__init__.py" in per_file_ignores
    assert list(per_file_ignores["__init__.py"]) == ["F401", "F403"]


def test_merge_adds_newline_at_end():
    """
    When [tool.ruff] is the last section in the file, the document should end
    with a single newline (normal EOF), NOT a double newline.

    When [tool.ruff] is followed by another section, a blank separator line
    should be inserted between them.
    """
    # Case 1: ruff is the last section — expect normal single-newline EOF
    source_toml_s = """[tool.ruff]
target-version = "py310"
"""
    upstream_ruff_s = """[tool.ruff]
line-length = 100
"""
    source_doc = tomlkit.parse(source_toml_s)
    upstream_ruff = cast("Any", tomlkit.parse(upstream_ruff_s))["tool"]["ruff"]

    merged_doc = ruff_sync.merge_ruff_toml(source_doc, upstream_ruff)
    merged_s = merged_doc.as_string()

    print(f"Merged Result (ruff last):\n{merged_s!r}")
    assert merged_s.endswith("\n"), "File should end with a single newline"
    assert not merged_s.endswith("\n\n"), "File should NOT end with a double newline"

    # Case 2: ruff is followed by another section — expect a blank separator line
    source_toml_with_next = """[tool.ruff]
target-version = "py310"

[tool.coverage.run]
include = ["foo.py"]
"""
    source_doc2 = tomlkit.parse(source_toml_with_next)
    upstream_ruff2 = cast("Any", tomlkit.parse(upstream_ruff_s))["tool"]["ruff"]

    merged_doc2 = ruff_sync.merge_ruff_toml(source_doc2, upstream_ruff2)
    merged_s2 = merged_doc2.as_string()

    print(f"Merged Result (ruff not last):\n{merged_s2!r}")
    assert "\n\n[tool.coverage" in merged_s2, (
        "Expected a blank line between [tool.ruff] and [tool.coverage.run]"
    )


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
