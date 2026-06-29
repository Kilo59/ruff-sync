# Agent Skill

`ruff-sync` ships an [Agent Skill](https://agentskills.io/home) — a structured, machine-readable file that teaches AI coding agents how to adopt and operate the tool. Any [Agent Skills–compatible](https://agentskills.io/what-are-skills) agent (GitHub Copilot, Claude Code, Cursor, etc.) will automatically discover and use it when working on your project.

## What Is an Agent Skill?

The [Agent Skills specification](https://agentskills.io/specification) is an open format for packaging domain expertise as a `SKILL.md` file. Agents load it when the task is relevant, gaining specialized knowledge without you needing to re-explain it every time.

## What the ruff-sync Skill Covers

The skill lives at [`.agents/skills/ruff-sync/`](https://github.com/Kilo59/ruff-sync/tree/main/src/ruff_sync/.agents/skills/ruff-sync/) and teaches agents:

| File | Contents |
|---|---|
| `SKILL.md` | Quick start, persistent config, common workflows, exit codes, and gotchas |
| `references/configuration.md` | Full `[tool.ruff-sync]` key reference |
| `references/troubleshooting.md` | Common errors and how to resolve them |
| `references/ci-integration.md` | GitHub Actions, GitLab CI, pre-commit, and Makefile recipes |

The skill uses [progressive disclosure](https://agentskills.io/specification#progressive-disclosure) — `SKILL.md` is concise enough to load in full when activated, and agents pull in the reference files only when they need specifics.

## Using the Skill in Your Project

`ruff-sync` supports the [Library Skills](https://library-skills.io/) specification. You can automatically install the agent skill using `uvx` (or `npx` if in a Node.js project):

```bash
uvx library-skills
```

This scans your environment, detects `ruff-sync` from your project's dependencies, and sets up a symlink at `.agents/skills/ruff-sync` pointing to the skill files bundled inside the installed package.

For Claude Code (which uses `.claude/skills` instead of `.agents/skills`), you can specify the targets or run:

```bash
uvx library-skills --claude
```

## Activation

Once the skill is in your agent's skill directory, it activates automatically for prompts like:

- *"Help me set up ruff-sync for this project"*
- *"How do I keep my Ruff config in sync across repos?"*
- *"Add a CI check for configuration drift"*
- *"My ruff-sync check is failing — how do I fix it?"*

## Keeping It Current

The skill is maintained alongside the codebase. Any change to CLI flags, exit codes, configuration keys, or URL handling includes an update to the skill files. See the [Contributing guide](contributing.md) for the skill maintenance checklist.
