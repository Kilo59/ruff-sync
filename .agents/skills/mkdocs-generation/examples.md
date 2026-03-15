# MkDocs Generation Examples

Real-world patterns from todoist-mcp and pydmp repositories.

## Simple Documentation (todoist-mcp)

Flat structure for smaller projects:

```
docs/
├── index.md
├── getting-started.md
├── configuration.md
└── tools.md
```

**mkdocs.yml nav:**
```yaml
nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - Configuration: configuration.md
  - MCP Tools: tools.md
```

**index.md:**
```markdown
# Todoist MCP Server

The Todoist MCP server is a Model Context Protocol (MCP) server for managing Todoist tasks from MCP clients like Claude Desktop.

Use this documentation to:

- Learn what the server can do
- Set up Docker-based or local development environments
- Configure environment variables and Redis caching
- Explore the available MCP tools for task and project management
```

## Complex Documentation (pydmp)

Nested structure for larger projects with API reference:

```
docs/
├── index.md
├── compatibility.md
├── guide/
│   ├── getting-started.md
│   ├── cli.md
│   ├── realtime-status.md
│   ├── encryption.md
│   └── migration.md
└── api/
    ├── panel.md
    ├── protocol.md
    ├── status.md
    ├── entities/
    │   ├── area.md
    │   ├── zone.md
    │   ├── output.md
    │   ├── user.md
    │   └── profile.md
    └── protocol/
        └── encryption.md
```

**mkdocs.yml nav:**
```yaml
nav:
  - Home: index.md
  - Panel Compatibility: compatibility.md
  - Guide:
      - Getting Started: guide/getting-started.md
      - CLI: guide/cli.md
      - Realtime Status (S3): guide/realtime-status.md
      - Encryption & User Data: guide/encryption.md
      - Migration: guide/migration.md
  - API Reference:
      - Panel: api/panel.md
      - Entities:
          - Area: api/entities/area.md
          - Zone: api/entities/zone.md
          - Output: api/entities/output.md
          - User Code: api/entities/user.md
          - User Profile: api/entities/profile.md
      - Protocol:
          - Protocol: api/protocol.md
          - Encryption: api/protocol/encryption.md
      - Realtime Server: api/status.md
```

## Index Page with Code Examples

```markdown
# PyDMP

PyDMP is a platform-agnostic Python library for controlling DMP alarm panels.

**Key Features:**

- **Dual APIs**: Choose async for modern applications or sync for simple scripts
- **High-level abstractions**: Work with panels, areas, zones, and outputs
- **Built-in rate limiting**: Automatic command throttling

## Installation

\`\`\`bash
pip install pydmp
\`\`\`

## Quick Start (Async)

\`\`\`python
import asyncio
from pydmp import DMPPanel

async def main():
    panel = DMPPanel()
    await panel.connect("192.168.1.100", "00001", "YOURKEY")
    await panel.update_status()
    areas = await panel.get_areas()
    await panel.disconnect()

asyncio.run(main())
\`\`\`

## Where to Next

- [Getting Started](guide/getting-started.md) - Installation and connection
- [CLI Guide](guide/cli.md) - Command-line interface
- [API Reference](api/panel.md) - Complete API documentation
```

## API Reference Page (mkdocstrings)

Minimal markdown that generates full API docs:

```markdown
# Panel API

::: pydmp.panel.DMPPanel

::: pydmp.panel_sync.DMPPanelSync
```

For entity docs:

```markdown
# Area

::: pydmp.area.Area

::: pydmp.area.AreaSync
```

## CLI Documentation Pattern

```markdown
# Command-Line Interface (CLI)

PyDMP ships with a CLI for common operations.

## Installation

\`\`\`bash
pip install pydmp[cli]
\`\`\`

## Configuration

The CLI expects a YAML config file:

\`\`\`yaml
panel:
  host: 192.168.1.100
  account: "00001"
  remote_key: "YOURKEY"
\`\`\`

## Commands

### Areas & Zones
\`\`\`bash
pydmp get-areas [--json|-j]
pydmp get-zones [--json|-j]
\`\`\`

### Arm/Disarm
\`\`\`bash
pydmp arm "1,2,3" [--bypass-faulted|-b] [--force-arm|-f]
pydmp disarm <AREA> [--json|-j]
\`\`\`

## Examples

\`\`\`bash
# View areas with debug logs
pydmp --debug get-areas

# Arm area 1
pydmp arm "1" --bypass-faulted
\`\`\`
```

## pyproject.toml Integration

```toml
[project.optional-dependencies]
docs = [
    "mkdocs>=1.5",
    "mkdocs-material>=9.4",
    "mkdocstrings[python]>=0.24",
    "mike>=2.0",
]
```

Install and build:
```bash
pip install -e ".[docs]"
mkdocs serve
mkdocs build
```
