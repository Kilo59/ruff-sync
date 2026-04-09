#!/usr/bin/env python3
"""Official screenshot generation script for ruff-sync.

Uses Textual's testing harness to launch the app headlessly,
navigate to specific views, and capture SVG screenshots.

Screenshots captured:
  dashboard.svg       -- Full app with Pyflakes (F) selected, colorful rule table populated
  search_omnibox.svg  -- Omnibox showing fuzzy search results for "import"
  legend_help.svg     -- The keyboard legend / help modal
  rule_details.svg    -- Rule detail inspector (NOT regenerated; existing file is authoritative)
"""

from __future__ import annotations

import asyncio
import os
import pathlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruff_sync.tui.widgets import ConfigTree

from ruff_sync.cli import Arguments
from ruff_sync.constants import DEFAULT_BRANCH, DEFAULT_EXCLUDE, OutputFormat
from ruff_sync.tui.app import RuffSyncApp

# Path to the directory where screenshots will be saved
SCREENSHOTS_DIR = pathlib.Path("docs/assets/screenshots")
SCREENSHOT_SAMPLE_TOML = SCREENSHOTS_DIR / "screenshot_sample.toml"


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


async def _navigate_to_pyflakes(tree: ConfigTree, pilot: object) -> bool:
    """Navigate down the tree until Pyflakes (F) is found and selected.

    Args:
        tree: The config tree widget.
        pilot: The Textual pilot.

    Returns:
        True if Pyflakes was found and selected, False otherwise.
    """
    for _ in range(200):
        node = tree.cursor_node
        if node:
            label = str(node.label.plain if hasattr(node.label, "plain") else node.label)
            if "Pyflakes" in label:
                # Press enter to trigger NodeSelected → fills the CategoryTable
                await pilot.press("enter")  # type: ignore[attr-defined]
                return True
        await pilot.press("down")  # type: ignore[attr-defined]
        await pilot.pause(0.02)  # type: ignore[attr-defined]
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
        # Wait generously for the background _prime_caches worker to finish.
        # This is critical — rule statuses and colors won't appear without it.
        await pilot.pause(3.0)

        tree: ConfigTree = app.query_one("#config-tree")  # type: ignore[assignment]

        # ── 1. Dashboard: Pyflakes (F) selected, colorful mixed-status table ──
        # Expand "Effective Rule Status" and walk down to Pyflakes (F)
        await pilot.press("home")
        await pilot.press("down")  # Move to "Effective Rule Status"
        await pilot.press("right")  # Expand node
        await pilot.pause(0.5)

        found = await _navigate_to_pyflakes(tree, pilot)
        if not found:
            print("  ⚠️ WARNING: Failed to find Pyflakes in tree — dashboard may be empty")

        # Give the CategoryTable time to populate and colorize
        await pilot.pause(2.0)

        path = SCREENSHOTS_DIR / "dashboard.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # ── 2. Legend / Help — captured BEFORE omnibox to avoid key-routing race ──
        await pilot.press("?")
        await pilot.pause(0.6)

        path = SCREENSHOTS_DIR / "legend_help.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # Dismiss modal; poll screen stack to confirm it's fully gone
        await pilot.press("escape")
        for _ in range(30):
            await pilot.pause(0.1)
            if len(app.screen_stack) == 1:
                break
        await pilot.pause(0.3)

        # ── 3. Omnibox: fuzzy search for "import" — shows cross-linter results ──
        # Searching for a concept (not an exact rule code) demonstrates how the
        # omnibox surfaces relevant rules from multiple linter families at once.
        await pilot.press("/")
        await pilot.pause(0.5)  # Wait for modal mount and input focus
        await pilot.press(*"import")
        await pilot.pause(0.8)  # Let results render

        path = SCREENSHOTS_DIR / "search_omnibox.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

    print("\n🎉 Screenshot generation complete!")
    print("   (rule_details.svg was NOT regenerated — existing file is authoritative)")


if __name__ == "__main__":
    # Ensure we run from the project root
    os.chdir(pathlib.Path(__file__).parent.parent)
    asyncio.run(generate_screenshots())
