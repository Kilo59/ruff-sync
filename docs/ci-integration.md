# CI Integration

`ruff-sync` is designed to be run in CI pipelines to ensure that all repositories in an organization stay in sync with the central standards.

## Usage in CI

The best way to use `ruff-sync` in CI is with the `check` command. If the configuration has drifted, `ruff-sync check` will exit with a non-zero code, failing the build.

### GitHub Actions

We recommend using `uv` to run `ruff-sync` in GitHub Actions.

```yaml
name: "Standards Check"

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ruff-sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Check Ruff Sync
        run: uvx ruff-sync check --semantic
```

### GitLab CI

```yaml
ruff-sync-check:
  image: python:3.12
  script:
    - pip install ruff-sync
    - ruff-sync check --semantic
```

## Best Practices

### Use `--semantic`

By default, `ruff-sync check` does a strict comparison of the TOML files. This means that if you manually reformat `pyproject.toml` or add a comment, the check will fail even if the actual Ruff rules are the same.

In CI, you usually only care about the functional configuration. Using `--semantic` ensures that minor formatting changes don't break your builds.

### Use a Dedicated Workflow

Running `ruff-sync` as a separate job in your linting workflow makes it easy to identify when a failure is due to configuration drift rather than a code quality issue.

### Automated PRs

Instead of just checking, some organizations prefer to have a bot automatically open a PR when the upstream configuration changes. You can achieve this by running `ruff-sync pull` and using an action like `create-pull-request`.
