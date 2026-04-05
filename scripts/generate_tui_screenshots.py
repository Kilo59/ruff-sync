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
ROOT_TOML = pathlib.Path("pyproject.toml")


def get_default_args() -> Arguments:
    """Create a default Arguments object for the TUI."""
    return Arguments(
        command="inspect",
        upstream=(),
        to=ROOT_TOML,
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
    print(f"📸 Generating screenshots in {SCREENSHOTS_DIR}...")

    args = get_default_args()
    app = RuffSyncApp(args)

    async with app.run_test(size=(120, 40)) as pilot:
        # 1. Main Dashboard (Initial View)
        # Wait for the background caches to prime
        await pilot.pause(0.5)
        path = SCREENSHOTS_DIR / "dashboard.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # 2. Rule Detail View
        # Navigate down into the tree to select a category/rule
        # (Assuming the structure: tool.ruff -> lint -> select)
        await pilot.press("down", "down", "down", "enter")
        await pilot.pause(0.2)
        path = SCREENSHOTS_DIR / "rule_details.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # 3. Omnibox / Search
        await pilot.press("/")
        await pilot.pause(0.1)
        # Type a search query
        await pilot.press(*"RUF012")
        await pilot.pause(0.1)
        path = SCREENSHOTS_DIR / "search_omnibox.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

        # Close search
        await pilot.press("escape")
        await pilot.pause(0.1)

        # 4. Legend / Help
        await pilot.press("?")
        await pilot.pause(0.1)
        path = SCREENSHOTS_DIR / "legend_help.svg"
        app.save_screenshot(str(path))
        print(f"  ✓ Saved {path}")

    print("\n🎉 Screenshot generation complete!")


if __name__ == "__main__":
    # Ensure we run from the project root
    os.chdir(pathlib.Path(__file__).parent.parent)
    asyncio.run(generate_screenshots())
