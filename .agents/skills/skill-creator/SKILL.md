---
name: skill-creator
description: >-
  Create or update Agent Skills to extend capabilities for specific tasks,
  frameworks, or domain-specific workflows. Use this when the user asks to
  "add a skill," "create a tool for X," or "teach the agent how to Y."
---

# Skill Creator Meta-Skill

This skill provides a systematic approach to creating and optimizing "Agent Skills" within the `.agents/skills/` directory.

## Available Scripts

- **`scripts/scaffold_skill.py`**: Automated scaffolding for new Agent Skill directories and `SKILL.md` templates.

## Workflow

1. **Scaffold the Skill**:
   - Run the scaffolding script to create the directory structure:
     ```bash
     uv run .agents/skills/skill-creator/scripts/scaffold_skill.py <name> \\
       --description "user intent" \\
       --keywords "key, word"
     ```
   - This creates `.agents/skills/<name>/SKILL.md` and standard subdirectories.

2. **Research & Plan**:
   - Determine the scope of the skill (e.g., CLI wrapper, documentation guide, testing helper).
   - Identify existing project artifacts (style guides, API specs, CI workflows) to pull information from.
   - Design a test case or a set of "should-trigger" queries.
   - See [references/quickstart.md](references/quickstart.md) for the basic structure.

3. **Define Frontmatter**:
   - `name`: Must match the folder name in `.agents/skills/`.
   - `description`: Write an imperative, user-intent-focused description.
   - See [references/optimizing-descriptions.md](references/optimizing-descriptions.md) for optimization tips.

4. **Develop the Procedure & Scripts**:
   - Favor procedural instructions ("To do X, run Y") over declarative ones.
   - Bundle complex logic in `scripts/` using [references/using-scripts.md](references/using-scripts.md).
   - Include a "Quick Start" section for the most common usecase.
   - Use checklists for multi-step workflows.

5. **Progressive Disclosure**:
   - If the skill is complex, move detailed references to a `references/` subdirectory.
   - See [references/best-practices.md](references/best-practices.md) for structuring tips.

6. **Validation & Iteration**:
   - Run the prompt *with* and *without* the skill instructions.
   - Use [references/evaluating-skills.md](references/evaluating-skills.md) to grade outputs with assertions.
   - Add a "Gotchas" section to address common pitfalls.
   - Iterate on instructions based on failed assertions or high variance.

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
- [Evaluating Skills](references/evaluating-skills.md) — Eval-driven iteration and assertions
- [Using Scripts](references/using-scripts.md) — Bundling logic and agentic script design
