# Installation

`ruff-sync` is a Python CLI tool. We recommend using **uv** for the best experience—it's fast, reliable, and allows you to run tools without managing global environments.

## ⚡ Recommended: Using `uv`

The easiest way to use `ruff-sync` is by installing it as a [uv tool](https://docs.astral.sh/uv/guides/tools/)

```bash
uv tool install ruff-sync
```

Once installed, you can simply run:

```bash
ruff-sync pull
```

### Alternative: Development Dependency

If you want to keep the version consistent across your team and locked to your project, add it to your development dependencies:

```bash
uv add --dev ruff-sync
# Then run it with:
uv run ruff-sync pull
```

---

## 🛠️ Other Installation Methods

=== "pipx"

    [pipx](https://github.com/pypa/pipx) is the recommended way to install Python CLIs globally in isolated environments.

    ```bash
    pipx install ruff-sync
    ```

=== "pip"

    You can install `ruff-sync` from PyPI using `pip`:

    ```bash
    pip install ruff-sync
    ```

    > [!WARNING]
    > We recommend using a virtual environment or `pipx` to avoid dependency conflicts with other global packages.

## Verifying Installation

Check that `ruff-sync` is installed correctly by running:

```bash
ruff-sync --version
```
