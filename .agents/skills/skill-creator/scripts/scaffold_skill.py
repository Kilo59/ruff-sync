# /// script
# dependencies = [
#     "rich",
# ]
# ///
from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys

from rich import print
from rich.panel import Panel

# The root directory for skills, derived relative to the script location:
# .agents/skills/skill-creator/scripts/scaffold_skill.py
# parent -> scripts/
# parent.parent -> skill-creator/
# parent.parent.parent -> skills/
SKILLS_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if SKILLS_ROOT.name != "skills" or SKILLS_ROOT.parent.name != ".agents":
    print(
        f"[red]Error:[/red] Invalid repository layout. "
        f"SKILLS_ROOT must be '.agents/skills', but got '{SKILLS_ROOT}'."
    )
    sys.exit(1)

SKILL_TEMPLATE = """---
name: {name}
description: >-
  Use this skill when {description}.
  Trigger on keywords like {keywords}.
---

# {name_title}

<!--
  PROGESSIVE DISCLOSURE (PD) RULES:
  - Keep this file UNDER 110 lines.
  - This file = PROCEDURAL (How-To, Workflows, Checklists).
  - Move deep-dive examples, logic trees, or recipes to references/.
-->

<High-level overview of the skill's purpose.>

## Quick Start

```bash
# Provide the most common command or procedure
<command>
```

## Common Workflows

### {name_title} Main Workflow

- [ ] Step 1: <action>
- [ ] Step 2: <action>
- [ ] Step 3: <action>

## Gotchas

- **<pitfall>**: <resolution>

## References

- [Examples & Recipes](references/quickstart.md) — (Move detailed examples here)
"""

QUICKSTART_TEMPLATE = """# {name_title} Examples & Recipes

This reference contains detailed illustrative examples, edge cases, and recipes
for the `{name}` skill.

## Recipe: Common Usecase

```python
# Detailed code example here
```

## Troubleshooting

- Problem A: <solution>
"""


class SkillScaffoldError(Exception):
    """Raised when skill scaffolding cannot be completed."""


def validate_kebab_case(name: str) -> None:
    """Validate that the name is kebab-case (lowercase, numbers, and hyphens)."""
    if not re.match(r"^[a-z0-9-]+$", name):
        msg = f"Invalid skill name '{name}'. Name must be kebab-case (e.g., 'my-cool-skill')."
        raise SkillScaffoldError(msg)


def scaffold_skill(name: str, description: str, keywords: str) -> None:
    """Scaffold a new skill directory and template.

    Raises:
        SkillScaffoldError: If the name is invalid or the directory already exists.
    """
    validate_kebab_case(name)

    skill_dir = SKILLS_ROOT / name
    if skill_dir.exists():
        msg = f"Skill directory '{skill_dir}' already exists."
        raise SkillScaffoldError(msg)

    try:
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
    except Exception as e:
        # Clean up if partially created
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        msg = f"Failed to create skill: {e}"
        raise SkillScaffoldError(msg) from e


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

    try:
        scaffold_skill(args.name, args.description, args.keywords)
    except SkillScaffoldError as e:
        print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[red]Unexpected Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
