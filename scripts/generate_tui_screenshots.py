#!/usr/bin/env python3
"""Official screenshot generation script for ruff-sync.

Uses Textual's testing harness to launch the app headlessly,
navigate to specific views, and capture SVG screenshots.

Screenshots captured:
  dashboard.svg       -- Full app with the Pyflakes (F) linter selected, colorful rule table
  search_omnibox.svg  -- Omnibox showing fuzzy search results for OMNIBOX_QUERY
  legend_help.svg     -- The keyboard legend / help modal
  rule_details.svg    -- Rule detail inspector (NOT regenerated; existing file is authoritative)
"""

from __future__ import annotations

import asyncio
import os
import pathlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from textual.pilot import Pilot

    from ruff_sync.tui.widgets import CategoryTable, ConfigTree

from ruff_sync.cli import Arguments
from ruff_sync.constants import DEFAULT_BRANCH, DEFAULT_EXCLUDE, OutputFormat
from ruff_sync.tui.app import RuffSyncApp

# ── File paths ────────────────────────────────────────────────────────────────
SCREENSHOTS_DIR: Final = pathlib.Path("docs/assets/screenshots")
SCREENSHOT_SAMPLE_TOML: Final = SCREENSHOTS_DIR / "screenshot_sample.toml"

# ── Widget selectors (CSS IDs) ────────────────────────────────────────────────
TREE_ID: Final = "#config-tree"
TABLE_ID: Final = "#category-table"

# ── Navigation targets ────────────────────────────────────────────────────────
# Label of the top-level tree node that groups all linter rules.
RULES_ROOT_LABEL: Final = "Effective Rule Status"
# The linter whose node we navigate to for the dashboard screenshot.
# Uses a substring match so minor wording changes (e.g. accent marks) don't break it.
DASHBOARD_LINTER_LABEL: Final = "Pyflakes"

# ── Search / omnibox ──────────────────────────────────────────────────────────
# Concept-level query (not an exact rule code) that demonstrates how the omnibox
# surfaces matching rules from multiple linter families at once.
OMNIBOX_QUERY: Final = "import"

# ── Polling tuning ────────────────────────────────────────────────────────────
# Maximum iterations when polling for a condition; each step pauses POLL_STEP_S seconds.
MAX_POLL_ITERS: Final = 50
POLL_STEP_S: Final = 0.1
# Max steps when walking the tree cursor looking for a labelled node.
MAX_TREE_WALK_STEPS: Final = 200


def get_default_args() -> Arguments:
    """Create a default Arguments object for the TUI."""
    return Arguments(
        command="inspect",
        upstream=(),
        to=SCREENSHOT_SAMPLE_TOML,
        exclude=DEFAULT_EXCLUDE,
        verbose=0,
        branch=DEFAULT_BRANCH,
        path=None,
        semantic=False,
        diff=True,
        init=False,
        pre_commit=False,
        save=None,
        output_format=OutputFormat.TEXT,
    )


def _node_label(tree: ConfigTree, /) -> str:
    """Return the plain-text label of the tree's currently focused node."""
    node = tree.cursor_node
    if node is None:
        return ""
    raw = node.label
    return str(raw.plain if hasattr(raw, "plain") else raw)


async def _walk_tree_to(tree: ConfigTree, pilot: Pilot[None], substring: str) -> bool:
    """Move the tree cursor down until a node whose label contains *substring* is found.

    Args:
        tree: The sidebar ConfigTree widget.
        pilot: The active Textual Pilot.
        substring: The substring to search for in node labels.

    Returns:
        True if the node was found (cursor is now on it), False if the walk
        exhausted MAX_TREE_WALK_STEPS without a match.
    """
    for _ in range(MAX_TREE_WALK_STEPS):
        if substring in _node_label(tree):
            return True
        await pilot.press("down")
        await pilot.pause(0.02)
    return False


async def _wait_for_condition(
    condition: object,
    *,
    pilot: Pilot[None],
    label: str = "condition",
) -> bool:
    """Poll *condition* (a callable) until it returns truthy or MAX_POLL_ITERS is reached.

    Args:
        condition: A zero-argument callable returning a truthy value when ready.
        pilot: The active Textual Pilot (used for controlled pausing).
        label: A human-readable name for the condition (used in warning messages).

    Returns:
        True if the condition became truthy within the timeout, False otherwise.
    """
    for _ in range(MAX_POLL_ITERS):
        if condition():  # type: ignore[operator]
            return True
        await pilot.pause(POLL_STEP_S)
    print(f"  ⚠️ WARNING: Timed out waiting for {label!r}")
    return False


async def generate_screenshots() -> None:
    """Run the app headlessly and capture screenshots of multiple views.

    NOTE: rule_details.svg is intentionally NOT regenerated here.
    The existing file was hand-verified as high quality. Run the TUI
    manually and use 'app.save_screenshot()' to update it if needed.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📸 Generating screenshots in {SCREENSHOTS_DIR} using {SCREENSHOT_SAMPLE_TOML}...")

    args = get_default_args()
    app = RuffSyncApp(args)

    async with app.run_test(size=(120, 40)) as pilot:
        tree: ConfigTree = app.query_one(TREE_ID)
        table: CategoryTable = app.query_one(TABLE_ID)

        # ── Wait for background cache priming to finish ────────────────────────
        # Check for `app.effective_rules` being populated rather than sleeping a
        # fixed duration — this is resilient to machine speed variations.
        await _wait_for_condition(
            lambda: bool(app.effective_rules),
            pilot=pilot,
            label="effective_rules populated",
        )

        # ── 1. Dashboard: Pyflakes (F) selected, colorful mixed-status table ──
        # Walk the tree to "Effective Rule Status" and expand it, then navigate
        # down to the DASHBOARD_LINTER_LABEL node.
        await pilot.press("home")
        found_rules_root = await _walk_tree_to(tree, pilot, RULES_ROOT_LABEL)
        if not found_rules_root:
            print(f"  ⚠️ WARNING: Could not find {RULES_ROOT_LABEL!r} node")

        await pilot.press("right")  # Expand the "Effective Rule Status" subtree
        await pilot.pause(0.3)

        found_linter = await _walk_tree_to(tree, pilot, DASHBOARD_LINTER_LABEL)
        if not found_linter:
            print(f"  ⚠️ WARNING: Could not find {DASHBOARD_LINTER_LABEL!r} node")

        # Select the node — fires NodeSelected → populates CategoryTable
        await pilot.press("enter")

        # Wait until the table actually has rows rather than sleeping a fixed amount.
        await _wait_for_condition(
            lambda: table.row_count > 0,
            pilot=pilot,
            label="CategoryTable row_count > 0",
        )

        path = SCREENSHOTS_DIR / "dashboard.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # ── 2. Legend / Help — captured BEFORE omnibox to avoid key-routing race ──
        await pilot.press("?")
        # Poll the screen stack: legend screen is ready once it's on top
        await _wait_for_condition(
            lambda: len(app.screen_stack) > 1,
            pilot=pilot,
            label="LegendScreen pushed",
        )

        path = SCREENSHOTS_DIR / "legend_help.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # Dismiss modal; poll until fully gone before sending further key events
        await pilot.press("escape")
        await _wait_for_condition(
            lambda: len(app.screen_stack) == 1,
            pilot=pilot,
            label="LegendScreen dismissed",
        )

        # ── 3. Omnibox: fuzzy search for OMNIBOX_QUERY ─────────────────────────
        await pilot.press("/")
        # Poll until the omnibox modal is mounted and on top
        await _wait_for_condition(
            lambda: len(app.screen_stack) > 1,
            pilot=pilot,
            label="OmniboxScreen pushed",
        )
        await pilot.press(*OMNIBOX_QUERY)
        # Wait for results to appear in the OptionList
        await pilot.pause(0.5)

        path = SCREENSHOTS_DIR / "search_omnibox.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

    print("\n🎉 Screenshot generation complete!")
    print("   (rule_details.svg was NOT regenerated — existing file is authoritative)")


if __name__ == "__main__":
    # Ensure we run from the project root
    os.chdir(pathlib.Path(__file__).parent.parent)
    asyncio.run(generate_screenshots())
