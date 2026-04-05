# Best Practices for Skill Creation

How to write skills that are well-scoped and calibrated to the task.

## 1. Spending Context Wisely

**Add what the agent lacks, omit what it knows.**
- **Bad**: "PDF (Portable Document Format) is a common file format..." (The agent knows this).
- **Good**: "Use `pdfplumber` for text extraction. For scans, fall back to `pytesseract`." (This is project-specific guidance).

## 2. Match Specificity to Fragility

**Low fragility (General task)**:
- Provide high-level goals and examples.
- Allow the agent to decide the best path (e.g., "Check database queries for SQLi...").

**High fragility (Specific/Dangerous task)**:
- Provide exact command sequences.
- Add warnings: "Do not modify flags or skip steps."
- Example: "Run exactly `python migrate.py --verify --backup`."

## 3. Favor Procedures over Declarations

- **Bad**: "This skill manages database migrations."
- **Good**: "To perform a migration: 1. Run script A. 2. Verify output B. 3. Update file C."
- Use checklists for multi-step workflows to help the agent track progress.

## 4. Progressive Disclosure

**Spending context wisely: Main file = Procedural. References = Illustrative.**
- **Limit**: Keep the main `SKILL.md` under **110 lines**.
- **The Entry Point**: Focus strictly on the "How-To" (workflows, checklists, high-level procedures).
- **The References**: Move anything that is "Illustrative" or "Dense" to the `references/` directory. This includes:
  - Complex decision trees or logic tables.
  - Multi-line code examples/recipes.
  - Full API references or error-code lookups.
  - Troubleshooting logs or edge-case post-mortems.
- This ensures the agent is only "weighed down" by relevant context when needed.

## 5. Gotchas & Common Pitfalls

- Include a "Gotchas" section to address recurring issues.
- Document reasons *why* certain approaches are forbidden (e.g., "Do not use library X because of security vulnerability Y").
- Link to troubleshooting guides for deeper dives.

## 6. Plan-Validate-Execute Loops

- Instruct the agent to create a plan first.
- Provide validation scripts to check work before "committing" (e.g., linting, type-checking, or running a validator).

## 7. Research Performance

**Prioritize fast, text-based tools over the browser.**
- **Fast**: Use `search_web` and `read_url_content` for documentation and general research.
- **Slow**: Avoid `read_browser_page` (browser subagent) unless the target site is a single-page app (SPA) that requires JavaScript rendering or authentication.
- **Guideline**: If you can see the content with a simple `curl`-like tool, do not spin up a browser. This saves significant time and keeps the agent focused.
