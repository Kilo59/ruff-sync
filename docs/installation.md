# Installation

`ruff-sync` is a Python CLI tool. We recommend using `uv` for the best experience, but it works with standard Python package managers as well.

## Recommended: Using `uv`

If you are using [uv](https://docs.astral.sh/uv/), you can run `ruff-sync` without installing it globally:

```bash
uvx ruff-sync pull
```

Or add it to your project's development dependencies:

```bash
uv add --dev ruff-sync
uv run ruff-sync pull
```

## Other Methods

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
