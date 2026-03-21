# Best Practices

When managing linter configurations across multiple projects with `ruff-sync`, following these best practices helps ensure a smooth, predictable, and manageable workflow for your entire organization.

---

## 📌 Pin Upstream Versions

Instead of syncing directly from the `main` branch, it can be beneficial to **pin to specific tags, releases, or stable branches**.

Linting rules evolve. If you sync from `main`, a new rule added to the central repository could instantly break CI across dozens of downstream projects the next time they run `ruff-sync` in an automated pipeline.

Instead, configure your upstream like this:

```toml
[tool.ruff-sync]
# Pin to a specific tag or commit for stability
upstream = "https://github.com/my-org/standards/blob/v1.2.0/pyproject.toml"
```

When you are ready to roll out new linting rules, you can update the version across repositories in a controlled manner.

---

## 🎯 Use Strategic Exclusions

Not every setting should be centralized. Some configurations are inherently project-specific.

Use the `exclude` option to prevent `ruff-sync` from overwriting configurations that should remain local.

For example, do not force all repositories to use the same Python target version, and allow projects to selectively ignore specific upstream rules that don't make sense locally:

```toml
[tool.ruff-sync]
upstream = "https://github.com/my-org/standards"
exclude = [
    # Always preserve local file-level exceptions (excluded by default)
    "lint.per-file-ignores",
    # Allow projects to define their own Python version
    "target-version",
    # Preserve local ignored rules that don't apply to this specific project
    "lint.ignore"
]
```

By excluding `lint.ignore`, a project can adopt the organization's standard `lint.select` list, but gracefully opt out of specific rules that cause issues in their specific domain without breaking the sync process.

---

## 🚦 Semantic Checks in CI

To ensure your repository hasn't drifted from your organization's unified standards, you should run `ruff-sync check --semantic` in your Continuous Integration pipeline.

**If you pin to a stable tag (as recommended above):**
Make this a **blocking check**. Since the upstream configuration won't change unexpectedly, any drift means a developer inadvertently modified the local rules. Failing the build ensures the repository stays perfectly compliant.

**If you sync directly from a moving branch (like `main`):**
We recommend making this an **informational, non-failing check**. If a new rule is added upstream while a developer is working on a feature, blocking their PR can cause frustration. Instead, pair the informational check with a **weekly automated workflow** that pulls down the latest configuration and opens a pull request. This groups linter updates into a single controllable PR that can be reviewed and tested in isolation.

See the [CI Integration Guide](ci-integration.md#automated-sync-prs) for an example GitHub Actions workflow that automatically syncs the configuration and opens a PR.

---

## 🏢 Hierarchical Configuration

For large organizations with distinct teams or sub-projects (like a frontend-heavy fullstack repo vs. a pure backend service), you can define multiple upstreams to create a hierarchy.

Because `ruff-sync` merges multiple upstreams sequentially (from top to bottom), the "last one wins." This allows you to have a strict company-wide base config, and a slightly looser (or tighter) team-specific config.

```toml
[tool.ruff-sync]
upstream = [
    # 1. Base company rules
    "https://github.com/my-org/standards/blob/main/base.toml",

    # 2. Team-specific tweaks (these override the base rules)
    "https://github.com/my-org/standards/blob/main/team-alpha.toml",
]
```
