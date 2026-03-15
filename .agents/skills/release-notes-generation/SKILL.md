---
name: release-notes-generation
description: Draft professional and categorized release notes for ruff-sync using GitHub CLI, git history, and the `invoke release` task.
---

# Release Notes Generation

This skill guides you through drafting high-quality release notes for `ruff-sync`. It leverages the `invoke release` task and GitHub CLI for context.

## Prerequisites

- **GitHub CLI (`gh`)**: Must be authenticated.
- **Invoke**: Dev tasks are defined in `tasks.py`.
- **Git**: Recent history and tags must be available.

## Workflow

### 1. Gather Context

Before drafting, understand what has changed since the last release.

```bash
# Get the latest release tag and notes
gh release list --limit 1
gh release view <tag>

# List merged PRs since the last tag
# Replace <tag> with the tag found above
gh pr list --state merged --search "merged:><tag-date>"

# Or simple git log
git log <tag>..HEAD --oneline
```

### 2. Create Draft Release

Use the project's built-in release task to scaffold the release. This task automatically tags the release based on the version in `pyproject.toml` and uses GitHub's `--generate-notes` feature to create a starting point.

```bash
# Create a draft release (default behavior of invoke release)
uv run invoke release --draft --skip-tests
```

> [!NOTE]
> `invoke release` will:
> 1. Check if you are on `main`.
> 2. Check for clean git state.
> 3. Create a GitHub Release with `--generate-notes`.

### 3. Refine Release Notes

GitHub's automatically generated notes are a good start but often lack professional categorization and narrative. Use the following structure for final refinement:

#### Categorization
- **🚀 Features**: New capabilities added to `ruff_sync`.
- **🐞 Bug Fixes**: Issues resolved in CLI, merging logic, or HTTP handling.
- **✨ Improvements**: Enhancements to existing features, performance, or logging.
- **📖 Documentation**: Updates to `README.md`, `docs/`, or docstrings.
- **🛠️ Maintenance**: Dependency updates, CI changes, or test refactoring.

#### Writing Style
- Use clear, action-oriented language (e.g., "Add support...", "Fix issue where...", "Refactor...").
- Link to PRs and contributors using their GitHub handles.
- Include a "Breaking Changes" section if applicable (use `[!WARNING]` alerts).

### 4. Finalize

Once the notes are drafted and refined, you can view the draft on GitHub or update it via CLI.

```bash
# View the draft notes
gh release view v<version>

# Edit the draft (opens your editor)
gh release edit v<version> --notes "your new notes"
```

## Tips

- **Consistency**: Refer to the `AGENTS.md` for project-specific terminology (e.g., "Upstream Layers").
- **Screenshots**: If the release includes significantly visible changes (e.g., new logging or CLI output formats), consider embedding a screenshot or recording in the notes.
- **Automated Summary**: You can ask the AI assistant to "Draft release notes based on the git log since <tag>" to get a structured summary before applying it to the release.
