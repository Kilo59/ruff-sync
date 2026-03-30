---
name: gh-issues
description: >-
  Create, update, comment on, and link GitHub issues using the gh CLI.
  Use when creating a new issue, adding sub-issues, cross-referencing issues,
  or posting large structured content (e.g. research docs) to GitHub.
---

# Working with GitHub Issues via the `gh` CLI

## Quick Reference

```bash
gh issue list                          # Open issues
gh issue list --limit 5               # Most recent 5
gh issue view <number>                 # Read issue body + metadata
gh issue view <number> --comments      # Include comments
gh issue create --title "..." --body "..." # Create issue (inline body — see Body Size warning)
gh issue create --title "..." --body-file /tmp/body.md  # Create from file (preferred)
gh issue comment <number> --body "..." # Post a comment
gh issue edit <number> --title "..."  # Edit issue metadata
gh issue close <number>               # Close an issue
```

---

## Creating Issues

### Always Use `--body-file` for Non-Trivial Bodies

> [!WARNING]
> **Never use inline `--body` with heredocs for large content.** A `gh issue create` with a
> multi-kilobyte `--body "$(cat << 'EOF' ... EOF)"` heredoc can hang for 10+ minutes before
> eventually succeeding (or silently timing out). This is a shell quoting / argument-size issue.
>
> **Rule of thumb**: If the body is more than ~20 lines, always write it to a temp file first.

```bash
# GOOD — write body to file, then reference it
cat > /tmp/issue-body.md << 'EOF'
## Summary
...long content...
EOF
gh issue create --title "My Issue" --body-file /tmp/issue-body.md

# BAD — inline heredoc with large bodies hangs
gh issue create --title "My Issue" --body "$(cat << 'EOF'
...long content...
EOF
)"
```

### Full `gh issue create` Options

```bash
gh issue create \
  --repo owner/repo \
  --title "Issue title" \
  --body-file /tmp/body.md \
  --label "enhancement" \
  --milestone "v1.0" \
  --assignee "@me"
```

- `--label` — must match an existing label name exactly (case-sensitive)
- `--milestone` — pass the milestone **title** string, not the number
- `--assignee "@me"` — assigns to the authenticated user

---

## Linking Issues

GitHub does not have a native parent/child relationship for issues. The convention is:

1. **Reference by number** in the issue body or a comment: `#102`
2. **Comment on the parent** after creating the child to make the link bidirectional

```bash
# After creating child issue #134, comment on the parent #102
gh issue comment 102 --body "Sub-issue created: #134 — short description."
```

GitHub automatically renders `#134` as a clickable link and shows a cross-reference in the
child issue's timeline. This is the standard convention used across open source projects.

---

## Reading Issues for Context

Always read the full issue before starting implementation work:

```bash
gh issue view 102                      # Body + metadata
gh issue view 102 --comments           # Include all comments (important for updated context)
gh issue list --milestone "v0.2.0"     # All issues in a milestone
gh issue list --search "formatter"     # Full-text search
```

---

## Posting Research / Reference Documents as Issues

If you have a long reference document (e.g., a `.md` file) to attach to an issue:

```bash
# 1. Create the issue using --body-file (NOT inline --body)
gh issue create \
  --title "GitLab CI codequality report support" \
  --body-file /tmp/issue-body.md \
  --label "enhancement"

# 2. Verify it was created
gh issue list --limit 3

# 3. Link it to the parent issue
gh issue comment <parent-number> --body "Sub-issue: #<new-number> — description."
```

---

## Common Gotchas

### 1. Large Inline `--body` Hangs the Shell

As noted above, `--body "$(cat ...)"` with large content can hang for many minutes. **Always use `--body-file`.**

### 2. Check the Issue Was Actually Created

After a slow `gh issue create`, run `gh issue list --limit 3` to confirm it succeeded before
retrying. Retrying blindly can create duplicate issues.

### 3. Labels and Milestones Must Pre-exist

`gh issue create --label "my-label"` will fail if `my-label` doesn't exist in the repo.
Check available labels with `gh label list`. Similarly for milestones.

### 4. `gh` Uses the Repo Inferred from `git remote`

When running in the repo directory, `gh` automatically targets the right repo. Pass
`--repo owner/repo` explicitly if you're unsure or running from a different directory.

### 5. Issue Numbers Are Stable — Just Look Them Up

If you lose track of a new issue's number after creating it:

```bash
gh issue list --limit 5   # shows most recently updated issues
```

The new issue will be at the top.

---

## Workflow: Create Issue from a Reference File

This is the pattern used when posting a research document (like a `.agents/` reference file)
as a GitHub issue body.

```
1. Write content to /tmp/issue-body.md
   - Include a preamble: what this is, what file it mirrors, link to parent issue
   - Then paste the full document content

2. gh issue create \
     --title "Descriptive title" \
     --body-file /tmp/issue-body.md \
     --label "enhancement" \
     --milestone "vX.Y.Z - ..."

3. gh issue list --limit 3   # confirm creation, note the issue number

4. gh issue comment <parent> --body "Sub-issue: #<new> — one-line description."
```

---

## References

- `gh issue --help` — full CLI reference
- [GitHub CLI manual](https://cli.github.com/manual/gh_issue)
- [GitHub cross-referencing issues](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls#issues-and-pull-requests)
