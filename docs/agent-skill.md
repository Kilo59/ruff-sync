# Agent Skill

`ruff-sync` ships an [Agent Skill](https://agentskills.io/home) — a structured, machine-readable file that teaches AI coding agents how to adopt and operate the tool. Any [Agent Skills–compatible](https://agentskills.io/what-are-skills) agent (GitHub Copilot, Claude Code, Cursor, etc.) will automatically discover and use it when working on your project.

## What Is an Agent Skill?

The [Agent Skills specification](https://agentskills.io/specification) is an open format for packaging domain expertise as a `SKILL.md` file. Agents load it when the task is relevant, gaining specialized knowledge without you needing to re-explain it every time.

## What the ruff-sync Skill Covers

The skill lives at [`.agents/skills/ruff-sync-usage/`](https://github.com/Kilo59/ruff-sync/tree/main/.agents/skills/ruff-sync-usage/) and teaches agents:

| File | Contents |
|---|---|
| `SKILL.md` | Quick start, persistent config, common workflows, exit codes, and gotchas |
| `references/configuration.md` | Full `[tool.ruff-sync]` key reference |
| `references/troubleshooting.md` | Common errors and how to resolve them |
| `references/ci-integration.md` | GitHub Actions, GitLab CI, pre-commit, and Makefile recipes |

The skill uses [progressive disclosure](https://agentskills.io/specification#progressive-disclosure) — `SKILL.md` is concise enough to load in full when activated, and agents pull in the reference files only when they need specifics.

## Using the Skill in Your Project

The skill is bundled in the `ruff-sync` repository itself. If you install `ruff-sync` from source or clone the repo, the skill is already present.

For agents that scan a configurable skill directory (e.g. `.agents/skills/`), copy the skill folder into your own project:

```bash
cp -r path/to/ruff-sync/.agents/skills/ruff-sync-usage .agents/skills/
```

Or reference the upstream directly if your agent supports remote skills.

## Activation

Once the skill is in your agent's skill directory, it activates automatically for prompts like:

- *"Help me set up ruff-sync for this project"*
- *"How do I keep my Ruff config in sync across repos?"*
- *"Add a CI check for configuration drift"*
- *"My ruff-sync check is failing — how do I fix it?"*

## Keeping It Current

The skill is maintained alongside the codebase. Any change to CLI flags, exit codes, configuration keys, or URL handling includes an update to the skill files. See the [Contributing guide](contributing.md) for the skill maintenance checklist.
