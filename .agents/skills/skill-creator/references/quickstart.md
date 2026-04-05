# Skill Creation Quickstart

A "Skill" is a directory containing a `SKILL.md` file that provides instructions to an agent.

## Basic Structure

Create your skill at `.agents/skills/<name>/SKILL.md`:

```markdown
---
name: <name>
description: >-
  Use this skill when <user intent/achievement>.
  Trigger on <keywords/context>.
---

# <Title>

<High-level overview of the skill's purpose.>

## Quick Start

```bash
# Provide the most common command or procedure
<command>
```

## Common Workflows

### Workflow 1

- [ ] Step 1: <action>
- [ ] Step 2: <action>
- [ ] Step 3: <action>

## Gotchas

- **<pitfall>**: <resolution>
- **<limitation>**: <alternative>

## References

- [Reference 1](references/ref1.md)
- [Reference 2](references/ref2.md)
```

## Directory Layout

```text
.agents/skills/<name>/
  SKILL.md              # Entry point (Frontmatter + Core Instructions)
  references/           # (Optional) Detailed guides
    config.md
    troubleshooting.md
  scripts/              # (Optional) Reusable scripts
    scaffold.py
  assets/               # (Optional) Static assets or images
```

## Activation Rules

1. **Frontmatter**: The `name` must match the parent folder exactly.
2. **Detection**: The agent reads the `description` at the start of a session. It only loads the full `SKILL.md` when it decides to "activate" based on the user's request.
3. **Imperative Phrase**: Always start descriptions with "Use this skill when..." to help the agent decide.
