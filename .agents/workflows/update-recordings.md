---
description: Regenerate CLI animation GIFs for documentation
---

Use this workflow to update the CLI animation GIFs when commands, output formatting, or CLI behavior changes.

### 1. Prerequisites
// turbo
1. Verify VHS is installed:
   ```bash
   export PATH="/opt/homebrew/bin:$PATH"
   which vhs && vhs --version
   ```
   If not installed: `brew install vhs`

### 2. Regenerate All Recordings
// turbo
1. Run the Invoke task:
   ```bash
   uv run invoke recordings
   ```
   *This processes all `.tape` files in `tapes/` and outputs GIFs to `docs/assets/recordings/`.*

### 3. Regenerate a Single Recording
// turbo
1. To regenerate only one:
   ```bash
   uv run invoke recordings --tape pull_basic
   ```

### 4. Verify Output
1. Check the `docs/assets/recordings/` directory for updated `.gif` files.
2. Open each GIF to verify it looks correct and the terminal output is legible.

### 5. Commit Changes
1. Stage and commit:
   ```bash
   git add docs/assets/recordings/*.gif tapes/*.tape
   git commit -m "docs: update CLI animation recordings"
   ```

---

### Adding a New Recording

1. **Create a new tape file** in `tapes/` (e.g., `tapes/my_feature.tape`).
2. **Start with** `Source tapes/_common.tape` to inherit shared settings.
3. **Set the output** path: `Output docs/assets/recordings/my_feature.gif`
4. **Add the commands** using VHS syntax (`Type`, `Enter`, `Sleep`, etc.).
5. **Test it**: `vhs tapes/my_feature.tape`
6. **Embed** the GIF in the relevant docs markdown file.

### Editing an Existing Recording

1. Edit the `.tape` file in `tapes/`.
2. Run `uv run invoke recordings --tape <name>` to regenerate just that GIF.
3. Review the output GIF.

### VHS Quick Reference (for agents)

| Command | Example | What it does |
|---|---|---|
| `Source` | `Source tapes/_common.tape` | Include settings from another tape |
| `Output` | `Output out.gif` | Set output file path and format |
| `Require` | `Require ruff-sync` | Fail fast if a program is missing |
| `Set` | `Set FontSize 16` | Configure terminal settings |
| `Type` | `Type "ruff-sync --help"` | Type characters into the terminal |
| `Enter` | `Enter` | Press the Enter key |
| `Sleep` | `Sleep 2s` | Wait for a specified duration |
| `Hide` | `Hide` | Stop recording (for setup commands) |
| `Show` | `Show` | Resume recording |
| `Ctrl+c` | `Ctrl+C` | Send Ctrl+C |
