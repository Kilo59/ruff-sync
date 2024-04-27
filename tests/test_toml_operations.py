from __future__ import annotations

from pprint import pformat as pf
from typing import TYPE_CHECKING

import pytest
import tomlkit
from tomlkit import TOMLDocument, array, key, table

if TYPE_CHECKING:
    from tomlkit.items import Table


def test_dot_noted_toml_items():
    """
    Test that tomlkit can create a TOML document with dot-noted items.
    """
    expected: str = """[tool.ruff]
target-version = "py38"
line-length = 120
lint.select = ["F", "ASYNC"]
"""

    doc = TOMLDocument()
    tool: Table = table(True)
    ruff: Table = table()
    ruff.update(
        {
            "target-version": "py38",
            "line-length": 120,
            key(["lint", "select"]): ["F", "ASYNC"],
        }
    )
    tool.append("ruff", ruff)
    doc.append("tool", tool)
    doc_str = doc.as_string()
    print(doc_str)
    assert doc.as_string() == expected


def test_neste_tables():
    """
    Test that tomlkit can create a TOML document with nested tables.
    """
    expected: str = """[tool.ruff]
target-version = "py38"
line-length = 120
lint.select = ["F", "ASYNC"]

[tool.ruff.lint.per-file-ignores]
"__init__.py" = [
    "F401", # unused import
    "F403", # star imports
]
"""
    doc = TOMLDocument()
    tool: Table = table(True)
    ruff: Table = table()
    per_file_ignores = table()
    pf_arry = array()
    pf_arry.add_line("F401", comment="unused import")
    pf_arry.add_line("F403", comment="star imports")
    pf_arry.add_line(indent="")
    per_file_ignores.add("__init__.py", pf_arry)
    ruff.update(
        {
            "target-version": "py38",
            "line-length": 120,
            key(["lint", "select"]): ["F", "ASYNC"],
        }
    )
    ruff.append("lint", {"per-file-ignores": per_file_ignores})
    tool.append("ruff", ruff)
    doc.append("tool", tool)

    doc_content = doc.unwrap()
    expected_content = tomlkit.parse(expected).unwrap()

    doc_str = doc.as_string()

    print(doc_str)

    print(f"\nexpected:\n{pf(expected_content)}\n\nactual\n{pf(doc_content)}")
    assert expected_content == doc_content
    assert doc_str == expected


if __name__ == "__main__":
    pytest.main([__file__, "-vv"])
