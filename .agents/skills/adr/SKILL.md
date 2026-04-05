# ADR (Architectural Decision Record) Skill

## Overview

Use this skill to capture, manage, and reference significant architectural decisions for `ruff-sync`. ADRs are stored internally in `.agents/decisions/` and provide a historical record of "Why" things are designed the way they are.

## When to Create an ADR

Create an ADR when:
- A significant architectural change is proposed (e.g., new internal AST, changing the merging strategy).
- A long-running refactoring strategy is initiated (e.g., the Type-Checking Refactoring).
- A decision is made that will impact future development and needs to be "remembered" by future agent sessions.
- A "Implementation Plan" has been approved and reaches a level of architectural significance that warrants long-term persistence.

## ADR Structure

Each ADR should be named `NNNN-slug.md` (e.g., `0001-type-refactoring-strategy.md`) and located in `.agents/decisions/`.

> [!IMPORTANT]
> **Use relative paths for ALL internal links.** Never use absolute paths (`file:///Users/...`) as they are machine-specific and break in different environments.

Use the following template:

```markdown
# ADR [NNNN]: [Short Title]

---
status: [proposed | accepted | superseded | deprecated]
date: YYYY-MM-DD
decider: [Agent | User]
---

## Context

What is the problem we are trying to solve? What are the constraints?

## Decision

What are we doing? Be specific about the architectural shift.

## Consequences

What are the trade-offs? What will be easier? What will be harder?

## References

- Links to PRs or Issues (use `gh-issues` skill).
- Links to other ADRs (e.g., "Supersedes [NNNN]").
- Links to implementation plans or research.
```

## Workflows

### 1. Creating a New ADR
1. Identify the need for a persistent architectural record.
2. Draft the ADR in `.agents/decisions/` using the next available number.
3. Update `.agents/decisions/README.md` with the new entry.
4. Reference the ADR in `AGENTS.md` if it represents a foundational shift.

### 2. Superseding an ADR
1. Create the new ADR (e.g., `0005`).
2. Mark the old ADR (e.g., `0002`) as `status: superseded`.
3. Add a link in the old ADR's `References` to the new one, and vice versa.

### 3. Graduation
Implementation plans in `.agents/` are often temporary. When a plan is completed, if its decisions are architecturally significant, "graduate" it by distilling its core decisions into an ADR.
