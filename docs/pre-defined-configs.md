# 📦 Pre-defined Configurations

While `ruff-sync` is designed to synchronize from *any* repository or URL, we provide a few curated configurations that you can use as a baseline for your projects.

These configurations are maintained in the [`configs/`](https://github.com/Kilo59/ruff-sync/tree/main/configs) directory of the `ruff-sync` repository.

---

## 🏗️ Kitchen Sink

An exhaustive configuration that explicitly enables and documents almost all available Ruff rules. This is ideal for teams that want a strict, "no-stone-unturned" approach to linting and formatting.

### Key Features
- **Strict Linting**: Enables almost all Ruff rules (over 700 rules).
- **Explicit Documentation**: Each rule or category is documented with comments explaining why it's enabled.
- **Safety First**: Includes security-related rules from `flake8-bandit`.

??? example "View `ruff.toml`"

    ```toml
    --8<-- "configs/kitchen-sink/ruff.toml"
    ```

### Usage

=== "Direct URL"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync/tree/main/configs/kitchen-sink
    ```

=== "Using --path"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync --path configs/kitchen-sink
    ```

=== "Using --branch"

    ```bash
    # Pin to a specific tag or branch
    ruff-sync https://github.com/Kilo59/ruff-sync --branch v0.1.2 --path configs/kitchen-sink
    ```

---

## ⚡ FastAPI & Async {: #fastapi-async }

Tailored specifically for modern, asynchronous web applications. It focuses on performance, correctness in `asyncio` code, and compatibility with popular frameworks like FastAPI and Pydantic.

### Key Features
- **Asyncio Specialized**: Includes rules for common `asyncio` pitfalls.
- **Pydantic Support**: Configured to play nicely with Pydantic's naming conventions and model definitions.
- **Web Security**: Includes essential security checks for web-facing applications.

??? example "View `ruff.toml`"

    ```toml
    --8<-- "configs/fastapi/ruff.toml"
    ```

### Usage

=== "Direct URL"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync/tree/main/configs/fastapi
    ```

=== "Using --path"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync --path configs/fastapi
    ```

=== "Using --branch"

    ```bash
    # Pin to a specific tag or branch
    ruff-sync https://github.com/Kilo59/ruff-sync --branch v0.1.2 --path configs/fastapi
    ```

---

## 📊 Data Science & Engineering

Optimized for data science workflows, focusing on readability and common patterns found in Jupyter notebooks, pandas, and numpy code.

### Key Features
- **Notebook Friendly**: Tailored rules for `.ipynb` files and cell-based development.
- **Documentation**: Focuses on clear docstrings and type hints for complex data pipelines.
- **Performance**: Includes rules to catch common performance issues in data processing loops.

??? example "View `ruff.toml`"

    ```toml
    --8<-- "configs/data-science-engineering/ruff.toml"
    ```

### Usage

=== "Direct URL"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync/tree/main/configs/data-science-engineering
    ```

=== "Using --path"

    ```bash
    ruff-sync https://github.com/Kilo59/ruff-sync --path configs/data-science-engineering
    ```

=== "Using --branch"

    ```bash
    # Pin to a specific tag or branch
    ruff-sync https://github.com/Kilo59/ruff-sync --branch v0.1.2 --path configs/data-science-engineering
    ```

---

## 🔧 Setting a Default

You can set your preferred curated configuration as the default in your `pyproject.toml` so you only need to run `ruff-sync` without arguments:

```toml
[tool.ruff-sync]
upstream = "https://github.com/Kilo59/ruff-sync"
path = "configs/fastapi"
branch = "main"  # or "v0.1.2" to pin to a specific git tag
```

---

## 📝 Contributing

Do you have a specialized Ruff configuration that you think would benefit the community? We welcome contributions of new curated configurations!

- **Join the Discussion**: [Issue #83: Community Curated Configs](https://github.com/Kilo59/ruff-sync/issues/83)
- **Contribution Guide**: [Contributing to ruff-sync](contributing.md)

We are particularly interested in configurations for:
- Machine Learning & AI
- CLI Tools
- Embedded Systems & MicroPython
- Large Monorepos
