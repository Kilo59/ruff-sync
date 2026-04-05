---
description: Regenerate TUI screenshots for documentation
---

Use this workflow to update the SVG screenshots of the Ruff-Sync TUI when the user interface, theme, or major features change.

### 1. Regenerate Screenshots
// turbo
1. Run the automated screenshot generation task:
   ```bash
   uv run invoke screenshots
   ```
   *This script launches the TUI headlessly using Textual's testing harness and captures key views to `docs/assets/screenshots/`.*

### 2. Verify Output
1. Check the `docs/assets/screenshots/` directory for updated `.svg` files:
   - `dashboard.svg`
   - `rule_details.svg`
   - `search_omnibox.svg`
   - `legend_help.svg`
2. Ensure the screenshots correctly reflect the current state of the application.

### 3. Update Documentation (Optional)
1. If new views were added or filenames changed, update the relevant markdown files in `docs/` or `mkdocs.yml`.

### 4. Commit Changes
1. Stage and commit the updated assets:
   ```bash
   git add docs/assets/screenshots/*.svg
   git commit -m "docs: update TUI screenshots"
   ```

---

### Adding a New Screenshot View

To add a new view to the automated screenshot rotation:

1.  **Modify the Script**: Edit `scripts/generate_tui_screenshots.py`.
2.  **Add Navigation**: Use `pilot` commands within the `async with app.run_test()` block:
    ```python
    # Navigate to the new view
    await pilot.press("control+f")  # Example: Open a specific dialog
    await pilot.pause(0.2)          # Give the UI time to animate
    ```
3.  **Capture the Screen**:
    ```python
    path = SCREENSHOTS_DIR / "my_new_view.svg"
    app.save_screenshot(str(path))
    ```
4.  **Update Documentation**: Add the new SVG to the relevant Markdown file or `mkdocs.yml`.
5.  **Regenerate**: Run `uv run invoke screenshots` to verify the new capture works as expected.
