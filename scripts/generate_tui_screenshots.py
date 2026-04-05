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
        await pilot.pause(1.0)

        # 1. Main Dashboard (Initial View)
        path = SCREENSHOTS_DIR / "dashboard.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # 2. Rule Detail View
        # Navigate to "Effective Rule Status" -> "Pyflakes (F)"
        # We start at Root ("Local Configuration"). Child 0 is "Effective Rule Status".
        await pilot.press("down")  # Select "Effective Rule Status"
        await pilot.press("right")  # Expand it if collapsed (no-op if expanded)
        await pilot.press("down")  # Select first linter, usually "Pyflakes (F)"
        await pilot.press("enter")  # Select the linter node to populate the table
        await pilot.pause(0.5)

        # Focus the table and select a specific rule (e.g., F401 or similar)
        # Tab moves focus from Tree to DataTable
        await pilot.press("tab")
        await pilot.pause(0.2)
        # Scroll down to a rule we want to showcase (e.g., F401)
        await pilot.press("down", "down")
        # Enter triggers RowSelected, which updates the inspector with documentation
        await pilot.press("enter")
        # Critical: Rule documentation fetch is async; wait long enough for it to render!
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
