# CI Integration

`ruff-sync` is designed to be run in CI pipelines to ensure that all repositories in an organization stay in sync with the central standards.

## Usage in CI

The best way to use `ruff-sync` in CI is with the `check` command. If the configuration has drifted, `ruff-sync check` will exit with a non-zero code, failing the build.

### GitHub Actions

We recommend using `uv` to run `ruff-sync` in GitHub Actions.

#### Basic Check

```yaml
name: "Standards Check"

on:
  pull_request:
    branches: [main]

jobs:
  ruff-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uvx ruff-sync check --semantic
```

#### Automated Sync PRs

Instead of just checking, you can have a bot automatically open a PR when the upstream configuration changes.

```yaml
name: "Upstream Sync"

on:
  schedule:
    - cron: '0 0 * * 1' # Every Monday at midnight
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Pull upstream
        run: uvx ruff-sync pull
      - name: Create Pull Request
        uses: peter-evans/create-pull-request@v6
        with:
          commit-message: "chore: sync ruff configuration from upstream"
          title: "chore: sync ruff configuration"
          body: "This PR synchronizes the Ruff configuration with the upstream source."
          branch: "ruff-sync-update"
```

### GitLab CI

```yaml
ruff-sync-check:
  image: python:3.12
  script:
    - pip install ruff-sync
    - ruff-sync check --semantic
  only:
    - merge_requests
    - main
```

---

You can use `ruff-sync` with `pre-commit` to ensure your configuration is always in sync before pushing.

See the [Pre-commit Guide](pre-commit.md) for details on using the official hooks.

!!! note
    Running `ruff-sync check` in pre-commit is fast because it only performs a network request if the local `pyproject.toml` is older than the upstream or if no cache exists.

---

## 💡 Best Practices

### Use `--semantic`

In CI, you usually only care about the functional configuration. Using `--semantic` ensures that minor formatting changes don't break your builds, while still guaranteeing that the actual rules are identical.

### Use a Dedicated Workflow

Running `ruff-sync` as a separate job in your linting workflow makes it easy to identify when a failure is due to configuration drift rather than a code quality issue.
