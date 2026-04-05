# /// script
# dependencies = [
#     "rich",
# ]
# ///
from __future__ import annotations

import argparse
import pathlib
import sys

from rich import print
from rich.panel import Panel

# The root directory for skills
SKILLS_ROOT = pathlib.Path(".agents/skills")

SKILL_TEMPLATE = """---
name: {name}
description: >-
  Use this skill when {description}.
  Trigger on keywords like {keywords}.
---

# {name_title}

<High-level overview of the skill's purpose.>

## Quick Start

```bash
# Provide the most common command or procedure
<command>
```

## Common Workflows

### {name_title} Setup

- [ ] Step 1: <action>
- [ ] Step 2: <action>
- [ ] Step 3: <action>

## Gotchas

- **<pitfall>**: <resolution>

## References

- [Quickstart](references/quickstart.md) — (Edit this to point to actual references)
"""

QUICKSTART_TEMPLATE = """# {name_title} Quickstart

This documentation covers the initial setup and common use cases for the `{name}` skill.

## Key Concepts

- Concept 1: <description>
- Concept 2: <description>

## Troubleshooting

- Problem A: <solution>
"""


def scaffold_skill(name: str, description: str, keywords: str) -> None:
    skill_dir = SKILLS_ROOT / name
    if skill_dir.exists():
        print(f"[red]Error: Skill directory '{skill_dir}' already exists.[/red]")
        sys.exit(1)

    # Create directories
    skill_dir.mkdir(parents=True)
    refs_dir = skill_dir / "references"
    refs_dir.mkdir()
    (skill_dir / "scripts").mkdir()
    (skill_dir / "assets").mkdir()

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(
        SKILL_TEMPLATE.format(
            name=name,
            name_title=name.replace("-", " ").title(),
            description=description,
            keywords=keywords,
        )
    )

    # Create Quickstart reference
    quickstart_md = refs_dir / "quickstart.md"
    quickstart_md.write_text(
        QUICKSTART_TEMPLATE.format(name=name, name_title=name.replace("-", " ").title())
    )

    print(
        Panel(
            f"[green]Successfully scaffolded new skill:[/green] [white]{name}[/white]\n"
            f"[dim]Directory: {skill_dir}[/dim]\n\n"
            f"[bold]Next steps:[/bold]\n"
            f"1. Edit [blue]{skill_md}[/blue] to add procedural instructions.\n"
            f"2. Add your reference docs in [blue]{refs_dir}[/blue].\n"
            f"3. Run an eval to verify activation with the new description.",
            title="Skill Scaffolder",
            expand=False,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new metadata-driven Agent Skill.")
    parser.add_argument("name", help="The kebab-case name of the skill (matching folder name).")
    parser.add_argument(
        "--description",
        default="user wants to perform a specific task",
        help="What achievement or intent triggers this skill.",
    )
    parser.add_argument(
        "--keywords",
        default="example, test",
        help="Comma-separated keywords for triggering.",
    )

    args = parser.parse_args()
    scaffold_skill(args.name, args.description, args.keywords)


if __name__ == "__main__":
    main()
