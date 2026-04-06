#!/usr/bin/env python3
"""Official screenshot generation script for ruff-sync.

Uses Textual's testing harness to launch the app headlessly,
navigate to specific views, and capture SVG screenshots.
"""

from __future__ import annotations

import asyncio
import os
import pathlib

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


async def generate_screenshots() -> None:
    """Run the app headlessly and capture screenshots of multiple views."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📸 Generating screenshots in {SCREENSHOTS_DIR} using {SCREENSHOT_SAMPLE_TOML}...")

    args = get_default_args()
    app = RuffSyncApp(args)

    async with app.run_test(size=(120, 40)) as pilot:
        # Increase initial pause to ensure background _prime_caches finishes
        # This is critical for rule statuses and details to show up!
        await pilot.pause(2.0)

        # 1. Main Dashboard (Initial View)
        # Expand "Effective Rule Status" so it looks more interesting
        await pilot.press("down", "right")
        await pilot.pause(0.5)

        path = SCREENSHOTS_DIR / "dashboard.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # 2. Rule Detail View
        # Navigate the Sidebar Tree to "Effective Rule Status" -> "Pyflakes (F)"
        # This populates the DataTable with the colorful mix of statuses (Enabled/Ignored/Disabled).
        await pilot.press("home")  # Ensure we start from the top
        await pilot.press("down")  # Select "Effective Rule Status"
        await pilot.press("right")  # Expand it if not already
        await pilot.pause(0.5)

        # Navigate down into the linters list until we hit "Pyflakes (F)"
        tree = app.query_one("#config-tree")
        for _ in range(100):
            await pilot.press("down")
            node = tree.cursor_node
            label = str(node.label.plain if hasattr(node.label, "plain") else node.label)
            if "Pyflakes" in label:
                # Select it to populate the table
                await pilot.press("enter")
                break

        # Give the table time to populate with colorful rows
        await pilot.pause(1.5)

        # Tab to the table and select rule F401 (Ignored)
        await pilot.press("tab")
        await pilot.pause(0.3)
        await pilot.press("enter")

        # Wait for the inspector to update with rule documentation
        await pilot.pause(1.0)

        path = SCREENSHOTS_DIR / "rule_details.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # 3. Omnibox / Search
        await pilot.press("/")
        await pilot.pause(0.3)
        # Type search: UP007 is a common, fixable rule
        await pilot.press(*"UP007")
        await pilot.pause(0.5)
        path = SCREENSHOTS_DIR / "search_omnibox.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # Close search
        await pilot.press("escape")
        await pilot.pause(0.2)

        # 4. Legend / Help
        await pilot.press("?")
        await pilot.pause(0.2)
        path = SCREENSHOTS_DIR / "legend_help.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

    print("\n🎉 Screenshot generation complete!")


if __name__ == "__main__":
    # Ensure we run from the project root
    os.chdir(pathlib.Path(__file__).parent.parent)
    asyncio.run(generate_screenshots())
