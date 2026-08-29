---
description: Standard step-by-step task lifecycle for AI agents working on ruff-sync
---

# Agent Task Lifecycle & Git Workflow

Follow this end-to-end lifecycle whenever starting a new feature, bug fix, refactor, or documentation update on `ruff-sync`.

```text
[1. Context] ➔ [2. Branch] ➔ [3. Test First ➔ Commit `test:`] ➔ [4. Implement & Validate ➔ Commit `feat:`/`fix:`] ➔ [5. Sync Docs/Skills ➔ Commit `docs:`] ➔ [6. Push & PR]
```

> [!IMPORTANT]
> **Commit Incrementally & Forward-Only (No Git Surgery)**:
> - Make focused, atomic commits as you complete each stage of work (`test:`, `feat:`, `fix:`, `docs:`). Do not wait until the very end.
> - **No need to polish history**: This repository uses **Squash and Merge** when merging PRs to `main`. There is no pressure to maintain an artificially pristine internal commit history.
> - **Avoid Git Surgery**: Do NOT use `git commit --amend` or `git reset` to rewrite past commits (standard `git rebase` against `main` is fine). Always make new forward-only commits for fixes, follow-ups, or formatting.

---

## 1. Intake & Context Gathering

Before writing any code:
1. **Read GitHub Issues**: If addressing an issue, inspect the description, labels, and all discussion comments:
   ```bash
   gh issue view <issue-number> --comments
   ```
2. **Check Architectural Decisions (ADRs)**: Review [`.agents/decisions/README.md`](../decisions/README.md) to understand existing architectural constraints and design patterns.
3. **Review Specialized Skills**: If working on TOML matching, warnings, Textual TUI, or documentation, review the relevant skill in [`.agents/skills/`](../skills/).

---

## 2. Sync & Branch from Latest `main`

> [!IMPORTANT]
> **Never make commits directly on `main`** unless explicitly instructed by the user. Always branch off the latest remote `main`.

1. **Verify working directory is clean**:
   ```bash
   git status
   ```
2. **Switch to `main` and pull latest changes**:
   ```bash
   git checkout main && git pull origin main
   ```
3. **Create and checkout a descriptive topic branch**:
   ```bash
   # Branch naming format: <type>/<issue-number>-<short-description>
   # Types: feat, fix, docs, refactor, test, chore
   git checkout -b feat/123-url-validation
   # or for an unlinked bugfix/task:
   git checkout -b fix/dotted-keys-proxy-table
   ```

---

## 3. Test First (TDD & Reproduction) ➔ *Commit Incrementally*

- **Bug Fixes**: Always write a reproduction test that **fails** before applying your fix and **passes** with it.
  - Edge cases and TOML merge tests go in `tests/test_corner_cases.py` or `tests/test_whitespace.py`.
  - For full lifecycle sync scenarios, scaffold a fixture triple in `tests/lifecycle_tomls/` using [`add-test-case.md`](add-test-case.md):
    ```bash
    uv run invoke new-case --name <case_name> --description "Description of edge case"
    ```
- **New Features**: Add unit tests in `tests/test_basic.py` or corresponding test module.
- **Testing Standards**: Follow [`.agents/TESTING.md`](../TESTING.md):
  - No `unittest.mock` or `MagicMock` (use DI, `respx`, or `pyfakefs`).
  - Strict async: decorate async tests with `@pytest.mark.asyncio`.
  - Terminate test files with `if __name__ == "__main__": pytest.main([__file__, "-vv"])`.

**Incremental Commit for Tests**:
```bash
git add tests/
git commit -m "test: add reproduction case for <issue-or-feature-summary>"
```

---

## 4. Implement & Validate Quality ➔ *Commit Incrementally*

- **Implement Following Project Conventions**:
  - **Imports**: Always include `from __future__ import annotations` as the first import. Use `import pathlib` and `import datetime as dt`.
  - **TOML Operations**: Always use `tomlkit`. Use `.unwrap()` when converting proxy objects to native Python objects.
  - **Sentinels**: Use `MissingType.SENTINEL` (`MISSING`) from `ruff_sync.constants` to distinguish absent fields from explicitly configured defaults.
  - **Typing**: Python 3.11 strict typing. Prefer `NamedTuple` for return types and `typing.Protocol` over abstract base classes.
  - **Warnings**: Follow [`.agents/skills/warnings-control/SKILL.md`](../skills/warnings-control/SKILL.md) for user-facing deprecations and `--strict` validation.

- **Run Mandatory 4-Step Validation Pipeline**:
  ```bash
  # 1. Lint and auto-fix
  uv run ruff check . --fix

  # 2. Format code
  uv run ruff format .

  # 3. Type check (strict mode)
  uv run mypy .

  # 4. Run test suite
  uv run pytest -vv
  ```

  Optional pre-commit run:
  ```bash
  uv run prek run --all-files
  ```

**Incremental Commit for Implementation**:
```bash
git add src/ tests/
git commit -m "feat(core): implement <feature-description> (#123)"
# or for a bugfix:
git commit -m "fix(merge): resolve <bug-description> (#123)"
```

---

## 5. Synchronize Documentation, Skills, & Assets ➔ *Commit Incrementally*

- **CLI or Config Changes**: If CLI flags, config keys in `[tool.ruff-sync]`, or exit codes change, **update the agent skill** at [`.agents/skills/ruff-sync/`](../skills/ruff-sync/) (which points to `src/ruff_sync/.agents/skills/ruff-sync/`).
- **User Documentation**: Update relevant pages in `docs/` or `mkdocs.yml` and test the docs build:
   ```bash
   uv run invoke docs --build
   ```
- **Terminal Recordings / Screenshots**:
  - If CLI output changed, regenerate VHS GIFs: [`update-recordings.md`](update-recordings.md).
  - If TUI layouts or screens changed, regenerate SVG screenshots: [`update-screenshots.md`](update-screenshots.md).
- **Architectural Shift**: If you made a major design decision, document it via the [ADR Skill](../skills/adr/SKILL.md).

**Incremental Commit for Documentation & Assets**:
```bash
git add docs/ .agents/ src/ruff_sync/.agents/
git commit -m "docs: update documentation and agent skills for <feature-name>"
```

---

## 6. Push & Open Pull Request

1. **Push Topic Branch**:
   ```bash
   git push -u origin <branch-name>
   ```

2. **Open Pull Request via `gh` CLI**:
   ```bash
   gh pr create \
     --title "feat: descriptive title" \
     --body $'## Summary\n- Description of changes\n\nCloses #<issue-number>'
   # Or use --body-file /tmp/pr-body.md for larger descriptions
   ```

3. **Verify CI**:
   ```bash
   gh pr checks
   ```
