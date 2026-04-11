# CLI Animation Plan for ruff-sync Documentation

## Goal

Add polished terminal GIF animations to `README.md` and the MkDocs documentation site to showcase ruff-sync's key workflows visually. Use a tool that produces **deterministic, version-controlled, agent-automatable** recordings.

---

## Tool Selection: Charmbracelet VHS

**[VHS](https://github.com/charmbracelet/vhs)** (19k+ ★) is the clear winner for this project. Here's why:

| Criterion | VHS | asciinema | terminalizer |
|---|---|---|---|
| Deterministic (code-as-config) | ✅ `.tape` files | ❌ records live | ❌ records live |
| GIF output | ✅ native | ⚠️ needs agg/svg-term | ✅ native |
| AI-agent friendly | ✅ simple DSL, text files | ❌ interactive recording | ❌ interactive recording |
| Version-controllable | ✅ tape files in git | ❌ JSON recordings | ❌ YAML recordings |
| Theming | ✅ built-in themes | ✅ | ⚠️ |
| CI-compatible | ✅ Docker image available | ⚠️ | ❌ |

### Why VHS is Agent-Friendly

VHS uses plain-text `.tape` files with a simple DSL (`Type`, `Enter`, `Sleep`, `Set`). An AI agent can:

1. **Write** tape files from scratch (just text)
2. **Edit** existing tape files to update commands when CLI behavior changes
3. **Run** `vhs <file>.tape` non-interactively to regenerate GIFs
4. **Validate** tape files syntactically with `vhs validate <file>.tape`

No UI interaction, no screen recording, no manual timing — everything is declarative.

---

## Prerequisites

### Install VHS and its dependencies

VHS requires `ttyd` and `ffmpeg` to be installed alongside it.

```bash
brew install vhs
# This also installs ttyd and ffmpeg as dependencies on macOS via Homebrew
```

Verify the installation:

```bash
vhs --version
which ttyd
which ffmpeg
```

### Install ruff-sync in the environment

The tape files will run `ruff-sync` commands, so it must be callable:

```bash
# From the project root:
uv pip install -e .
```

---

## Directory Structure

Create the following directory structure:

```
docs/
  assets/
    recordings/           # ← NEW: output GIFs go here
      pull_basic.gif
      check_drift.gif
      init_project.gif
      check_in_sync.gif
      validate_strict.gif
      help_overview.gif
tapes/                    # ← NEW: VHS tape source files
  _common.tape            # shared settings (sourced by all tapes)
  pull_basic.tape
  check_drift.tape
  init_project.tape
  check_in_sync.tape
  validate_strict.tape
  help_overview.tape
```

### Step-by-step directory creation

```bash
mkdir -p docs/assets/recordings
mkdir -p tapes
```

### Add `docs/assets/recordings/` to `.gitignore` (optional)

If GIFs should be tracked in git (recommended for docs), do NOT add them to `.gitignore`. If they should be regenerated in CI only, add:

```
# .gitignore
docs/assets/recordings/*.gif
```

> [!IMPORTANT]
> **Recommendation**: Track the GIFs in git so they display on GitHub without CI. They are usually 200-500 KB each.

---

## Tape Files

### Shared Settings: `tapes/_common.tape`

This file defines the visual settings reused by all tape files via VHS's `Source` command.

```tape
# tapes/_common.tape
# Shared VHS settings for ruff-sync documentation recordings.
#
# All individual tape files should `Source` this file at the top.

# ── Terminal appearance ──────────────────────────────────────────
Set Shell "bash"
Set FontFamily "JetBrains Mono"
Set FontSize 16
Set Width 1200
Set Height 600
Set LetterSpacing 1
Set LineHeight 1.2
Set Padding 20
Set Theme "Catppuccin Mocha"

# ── Typing behavior ─────────────────────────────────────────────
Set TypingSpeed 40ms

# ── Cursor ───────────────────────────────────────────────────────
Set CursorBlink false
```

> [!NOTE]
> The `Source` command in VHS lets tape files inherit settings from `_common.tape`. This keeps styling consistent and editable from one place.

---

### Tape 1: `tapes/pull_basic.tape` — Basic Sync

**Scenario**: Show the core workflow — pulling ruff config from an upstream repo.

**Demonstrates**: The primary use case, colorful terminal output, speed of the tool.

**Where it goes**: `README.md` hero section, `docs/index.md`, `docs/usage.md`

```tape
# tapes/pull_basic.tape
# Demonstrates: Basic ruff-sync pull from an upstream repository.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/pull_basic.gif

# Show the current state of pyproject.toml
Type "cat pyproject.toml | head -20"
Enter
Sleep 1.5s

# Run ruff-sync against the upstream
Type "ruff-sync https://github.com/Kilo59/ruff-sync -v"
Enter
Sleep 4s

# Show what changed
Type "git diff pyproject.toml | head -30"
Enter
Sleep 3s

# Clean up
Hide
Type "git checkout pyproject.toml"
Enter
Sleep 500ms
Show

Sleep 1s
```

---

### Tape 2: `tapes/check_drift.tape` — Detecting Configuration Drift

**Scenario**: Show `ruff-sync check` detecting drift, displaying a diff, and exiting non-zero.

**Demonstrates**: CI use case, colored diff output, exit code behavior.

**Where it goes**: `docs/usage.md` (Checking for Drift section), `docs/ci-integration.md`, `README.md` (CI section)

> [!IMPORTANT]
> This tape requires the local `pyproject.toml` to be intentionally out of sync with the upstream to produce a diff. The setup steps below use a temporary modification that is hidden from the recording.

```tape
# tapes/check_drift.tape
# Demonstrates: Catching configuration drift with `ruff-sync check`.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/check_drift.gif

# Silently introduce drift so the check fails
Hide
Type "cp pyproject.toml pyproject.toml.bak"
Enter
Sleep 300ms
# Remove a rule to simulate drift
Type `python3 -c "
t = open('pyproject.toml').read()
t = t.replace('\"PERF\",\n', '')
open('pyproject.toml', 'w').write(t)
"`
Enter
Sleep 500ms
Show

# Run the check command
Type "ruff-sync check --semantic -v"
Enter
Sleep 4s

# Show the exit code
Type "echo \"Exit code: $?\""
Enter
Sleep 2s

# Restore the original file (hidden)
Hide
Type "mv pyproject.toml.bak pyproject.toml"
Enter
Sleep 300ms
Show

Sleep 1s
```

---

### Tape 3: `tapes/init_project.tape` — Bootstrapping a New Project

**Scenario**: Show `ruff-sync --init` scaffolding a brand-new `pyproject.toml` in an empty directory.

**Demonstrates**: Zero-config bootstrapping, `--init` flag, the generated `[tool.ruff-sync]` section.

**Where it goes**: `docs/usage.md` (Initializing section), `docs/index.md` (Quick Start)

```tape
# tapes/init_project.tape
# Demonstrates: Bootstrapping a new project with --init.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/init_project.gif

# Create and enter a fresh directory
Type "mkdir /tmp/my-new-project && cd /tmp/my-new-project"
Enter
Sleep 500ms

Type "ls -la"
Enter
Sleep 1s

# Initialize from an upstream
Type "ruff-sync https://github.com/Kilo59/ruff-sync --init -v"
Enter
Sleep 4s

# Show the generated file
Type "cat pyproject.toml"
Enter
Sleep 3s

# Clean up (hidden)
Hide
Type "cd - && rm -rf /tmp/my-new-project"
Enter
Sleep 300ms
Show

Sleep 1s
```

---

### Tape 4: `tapes/check_in_sync.tape` — Config is In Sync

**Scenario**: Show `ruff-sync check` passing (exit 0) when config is already in sync.

**Demonstrates**: Happy-path CI result, green success output.

**Where it goes**: `docs/ci-integration.md`, `docs/usage.md`

```tape
# tapes/check_in_sync.tape
# Demonstrates: Happy path — config is already in sync.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/check_in_sync.gif

# Run the check — should pass since we're dogfooding our own config
Type "ruff-sync check --semantic -v"
Enter
Sleep 4s

# Confirm exit code
Type "echo \"Exit code: $?\""
Enter
Sleep 2s

Sleep 1s
```

---

### Tape 5: `tapes/validate_strict.tape` — Validation and Strict Mode

**Scenario**: Show `--validate` and `--strict` flags in action.

**Demonstrates**: Config validation, strict mode catching deprecated rules, error output.

**Where it goes**: `docs/usage.md` (Validating Before Writing section)

```tape
# tapes/validate_strict.tape
# Demonstrates: --validate and --strict flags.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/validate_strict.gif

# First show normal validation passing
Type "ruff-sync --validate -v"
Enter
Sleep 4s

Type ""
Enter
Sleep 500ms

# Now show strict mode
Type "ruff-sync --strict -v"
Enter
Sleep 4s

Sleep 2s
```

---

### Tape 6: `tapes/help_overview.tape` — Help Output

**Scenario**: Show the `--help` output for the tool and subcommands.

**Demonstrates**: Available commands, flags, general CLI structure.

**Where it goes**: `README.md`, `docs/usage.md` (Command Reference section)

```tape
# tapes/help_overview.tape
# Demonstrates: CLI help output overview.

Source tapes/_common.tape

Require ruff-sync

Output docs/assets/recordings/help_overview.gif

Set Height 700

# Main help
Type "ruff-sync --help"
Enter
Sleep 3s

# Pull help
Type "ruff-sync pull --help"
Enter
Sleep 3s

# Check help
Type "ruff-sync check --help"
Enter
Sleep 3s

Sleep 1s
```

---

## Invoke Task for Regeneration

Add a new Invoke task to `tasks.py` so recordings can be regenerated with a single command.

### Task definition

Add the following task to `tasks.py`:

```python
@task(
    help={
        "tape": "Specific tape file to record (e.g. 'pull_basic'). Default: all tapes.",
    },
)
def recordings(ctx, tape=None):
    """Regenerate CLI animation GIFs from VHS tape files."""
    import pathlib

    tapes_dir = pathlib.Path("tapes")
    if not tapes_dir.exists():
        print("❌ tapes/ directory not found. Run from the project root.")
        raise SystemExit(1)

    # Check VHS is installed
    result = ctx.run("which vhs", hide=True, warn=True)
    if not result.ok:
        print("❌ VHS is not installed. Install with: brew install vhs")
        raise SystemExit(1)

    if tape:
        tape_file = tapes_dir / f"{tape}.tape"
        if not tape_file.exists():
            print(f"❌ Tape file not found: {tape_file}")
            raise SystemExit(1)
        tape_files = [tape_file]
    else:
        # Process all tape files except _common.tape
        tape_files = sorted(
            f for f in tapes_dir.glob("*.tape") if not f.name.startswith("_")
        )

    if not tape_files:
        print("⚠️ No tape files found in tapes/")
        return

    print(f"🎬 Recording {len(tape_files)} tape(s)...")
    for tf in tape_files:
        print(f"  📼 {tf.name}")
        ctx.run(f"vhs {tf}")

    print("\n🎉 All recordings complete!")
    print("   Output: docs/assets/recordings/")
```

### Register the task alias

In the Invoke `ns` (namespace) collection at the bottom of `tasks.py`, add:

```python
ns.add_task(recordings)
```

### Usage

```bash
# Regenerate all recordings
uv run invoke recordings

# Regenerate a specific recording
uv run invoke recordings --tape pull_basic
```

---

## Documentation Integration

### README.md

Add the hero GIF right after the banner image (line ~2):

```markdown
<p align="center">
  <img src="https://raw.githubusercontent.com/Kilo59/ruff-sync/main/docs/assets/ruff_sync_banner.png" alt="ruff-sync banner" style="max-width: 600px; width: 100%; height: auto; margin-bottom: 1rem;">
  <br>
  <img src="https://raw.githubusercontent.com/Kilo59/ruff-sync/main/docs/assets/recordings/pull_basic.gif" alt="ruff-sync pull demo" style="max-width: 600px; width: 100%; height: auto;">
  <br>
  <!-- badges -->
```

Add the check drift animation in the CI Integration section (~line 287):

```markdown
## CI Integration

![ruff-sync check detecting drift](docs/assets/recordings/check_drift.gif)
```

### docs/index.md

Add the hero GIF after the banner:

```markdown
![ruff-sync banner](assets/ruff_sync_banner.png)

![ruff-sync pull demo](assets/recordings/pull_basic.gif)
```

Add the init GIF in the Quick Start section:

```markdown
### 1. Initialize a new project (Optional)

![Bootstrapping a new project with --init](assets/recordings/init_project.gif)
```

### docs/usage.md

Add animations inline with each section:

1. **The Basic Sync** → `pull_basic.gif`
2. **Checking for Drift** → `check_drift.gif`
3. **Validating Before Writing** → `validate_strict.gif`

Example:

```markdown
## 🌟 Common Workflows

### The Basic Sync

![Basic ruff-sync pull](assets/recordings/pull_basic.gif)

If you want to pull rules from a central repository...
```

### docs/ci-integration.md

Add the check animations:

```markdown
![Config in sync](assets/recordings/check_in_sync.gif)

![Config drift detected](assets/recordings/check_drift.gif)
```

---

## Agent Workflow for Updating Recordings

Create a new workflow file at `.agents/workflows/update-recordings.md`:

```markdown
---
description: Regenerate CLI animation GIFs for documentation
---

Use this workflow to update the CLI animation GIFs when commands, output formatting, or CLI behavior changes.

### 1. Prerequisites
// turbo
1. Verify VHS is installed:
   ```bash
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
```

---

## Optional: CI Workflow for Recording Validation

Add a GitHub Actions workflow that validates tape files (but doesn't regenerate GIFs) on every PR that touches `tapes/`:

```yaml
# .github/workflows/validate-tapes.yaml
name: Validate VHS Tapes

on:
  pull_request:
    paths:
      - "tapes/**"

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install VHS
        run: |
          sudo mkdir -p /etc/apt/keyrings
          curl -fsSL https://repo.charm.sh/apt/gpg.key | sudo gpg --dearmor -o /etc/apt/keyrings/charm.gpg
          echo "deb [signed-by=/etc/apt/keyrings/charm.gpg] https://repo.charm.sh/apt/ * *" | sudo tee /etc/apt/sources.list.d/charm.list
          sudo apt update && sudo apt install -y vhs
      - name: Validate tape files
        run: |
          for tape in tapes/*.tape; do
            if [[ "$(basename "$tape")" == _* ]]; then continue; fi
            echo "Validating $tape..."
            vhs validate "$tape"
          done
```

> [!TIP]
> Full GIF regeneration can be done manually or in a separate CI job since it's slow and requires `ttyd` + `ffmpeg`. The validation-only step is fast and catches syntax errors early.

---

## Execution Checklist

| # | Step | Command / Action |
|---|---|---|
| 1 | Install VHS | `brew install vhs` |
| 2 | Create directories | `mkdir -p docs/assets/recordings tapes` |
| 3 | Create `tapes/_common.tape` | Copy from [Shared Settings](#shared-settings-tapes_commontape) above |
| 4 | Create all 6 tape files | Copy from [Tape Files](#tape-files) section above |
| 5 | Test one tape | `vhs tapes/help_overview.tape` (fastest, no side effects) |
| 6 | Add Invoke task to `tasks.py` | Copy from [Invoke Task](#invoke-task-for-regeneration) above |
| 7 | Generate all recordings | `uv run invoke recordings` |
| 8 | Review all GIFs | Open `docs/assets/recordings/*.gif` |
| 9 | Integrate into README.md | Follow [README.md](#readmemd) integration instructions |
| 10 | Integrate into MkDocs pages | Follow [docs/ integration](#documentation-integration) instructions |
| 11 | Create agent workflow | Copy to `.agents/workflows/update-recordings.md` |
| 12 | (Optional) Add CI validation | Copy [CI workflow](#optional-ci-workflow-for-recording-validation) to `.github/workflows/` |
| 13 | Commit everything | `git add tapes/ docs/assets/recordings/ .agents/workflows/update-recordings.md` |

---

## Notes for the Implementing Agent

1. **Run tapes from the project root.** VHS will execute commands in the current working directory. Tape files reference relative paths like `tapes/_common.tape`.

2. **The `check_drift.tape` needs intentional drift.** It uses `Hide`/`Show` to silently modify `pyproject.toml` before running the check, then restores it. The implementing agent must ensure the Python one-liner in the tape actually removes a rule that exists in the current file.

3. **Font availability.** The `JetBrains Mono` font is specified in `_common.tape`. If not installed on the system, VHS will fall back to a default monospace font. For consistent results, install it: `brew install --cask font-jetbrains-mono`.

4. **Timing tuning.** The `Sleep` durations in each tape are estimates. After generating, review the GIFs and adjust:
   - Increase `Sleep` if output is cut off
   - Decrease `Sleep` if there's too much dead time
   - Adjust `TypingSpeed` in `_common.tape` for faster/slower typing animation

5. **Theme choice.** `Catppuccin Mocha` was chosen to match the dark-mode aesthetic of the MkDocs Material theme. If the project switches to a light theme, change to `Catppuccin Latte` or `One Light` in `_common.tape`.

6. **GIF file sizes.** Target under 500 KB per GIF. If a recording is too large:
   - Reduce the terminal `Width`/`Height`
   - Shorten `Sleep` durations
   - Reduce the amount of output shown (pipe through `head`)
