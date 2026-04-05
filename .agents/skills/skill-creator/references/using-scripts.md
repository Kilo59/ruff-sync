# Using Scripts in Skills

Bundling executable logic within your skills makes them more powerful and reliable than instruction-only skills.

## 1. One-off Commands

Use tool runners to invoke common utilities without pre-installing them.
- **Python**: `uvx ruff check .` or `pipx run black .`
- **Node.js**: `npx eslint@9 --fix .`
- **Go**: `go run golang.org/x/tools/cmd/goimports@latest .`

**Pin versions** (e.g., `eslint@9.0.0`) for reproducibility.

## 2. Self-Contained Scripts (`scripts/`)

For complex logic, bundle a script in the `scripts/` directory.

### Python (PEP 723)
Use inline dependency metadata so the script is self-documenting and runnable via `uv run`.

```python
# /// script
# dependencies = [
#     "httpx",
#     "rich",
# ]
# ///
import httpx
from rich import print

# ... script logic ...
```

### Deno / Bun
TypeScript runs natively without `package.json`.
- **Deno**: `deno run --allow-read scripts/process.ts`
- **Bun**: `bun run scripts/process.ts`

## 3. Designing for Agentic Use

- **No Interactive Prompts**: Scripts should fail with a clear error and usage instructions rather than hanging for input.
- **Helpful `--help`**: Ensure the agent can run `python scripts/my_script.py --help` to understand flags and examples.
- **Structured Output**: Prefer JSON or CSV over whitespace-aligned tables for easier parsing by the agent.
- **Idempotency**: "Create if not exists" is safer than failing on duplicates, as agents may retry commands.
- **Meaningful Exit Codes**: Use distinct codes for "Not Found," "Invalid Args," and "System Error."

## 4. Referencing from SKILL.md

Document the available scripts clearly in your core instructions:

```markdown
## Available Scripts
- **`scripts/validate.py`**: Validates input data and returns a JSON report.
- **`scripts/generate_chart.py`**: Creates a bar chart from the validation report.

## Workflow
1. Run validation: `uv run scripts/validate.py input.json` -> `results.json`.
2. Generate chart: `uv run scripts/generate_chart.py results.json`.
```
