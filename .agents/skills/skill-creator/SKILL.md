---
name: skill-creator
description: >-
  Create or update Agent Skills to extend capabilities for specific tasks,
  frameworks, or domain-specific workflows. Use this when the user asks to
  "add a skill," "create a tool for X," or "teach the agent how to Y."
---

# Skill Creator Meta-Skill

This skill provides a systematic approach to creating and optimizing "Agent Skills" within the `.agents/skills/` directory.

## Skill Creation Workflow

Follow these steps when tasked with creating a new skill:

1. **Research & Plan**:
   - Determine the scope of the skill (e.g., CLI wrapper, documentation guide, testing helper).
   - Identify existing project artifacts (style guides, API specs, CI workflows) to pull information from.
   - See [references/quickstart.md](references/quickstart.md) for the basic structure.

2. **Define Frontmatter**:
   - `name`: Must match the folder name in `.agents/skills/`.
   - `description`: Write an imperative, user-intent-focused description.
   - See [references/optimizing-descriptions.md](references/optimizing-descriptions.md) for optimization tips.

3. **Develop the Procedure**:
   - Favor procedural instructions ("To do X, run Y") over declarative ones.
   - Include a "Quick Start" section for the most common use case.
   - Use checklists for multi-step workflows.

4. **Progressive Disclosure**:
   - If the skill is complex, move detailed references to a `references/` subdirectory.
   - See [references/best-practices.md](references/best-practices.md) for structuring tips.

5. **Validation Loop (Plan-Validate-Execute)**:
   - Create a test case or a set of "should-trigger" queries.
   - Verify the skill's instructions lead to the desired outcome.
   - Add a "Gotchas" section to address common pitfalls.

## Skill Quality Checklist

- [ ] **Frontmatter**: Does the name match the directory name?
- [ ] **Description**: Is it imperative ("Use this skill when...") and under 1024 characters?
- [ ] **Procedural**: Does it provide clear, actionable steps for the agent to follow?
- [ ] **Context**: Does it include project-specific context (e.g., using `uv run`, `gh`, `ruff`)?
- [ ] **Specificity**: Does the level of detail match the fragility of the task?

## References

- [Quickstart](references/quickstart.md) — Basic SKILL.md structure
- [Best Practices](references/best-practices.md) — How to scope and calibrate skills
- [Optimizing Descriptions](references/optimizing-descriptions.md) — Reliable triggering strategies
