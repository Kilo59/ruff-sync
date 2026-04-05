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

- Keep `SKILL.md` under 150 lines if possible.
- Move details (error tables, full API references, edge case logs) to `references/`.
- This ensures the agent is only "weighed down" by relevant context when needed.

## 5. Gotchas & Common Pitfalls

- Include a "Gotchas" section to address recurring issues.
- Document reasons *why* certain approaches are forbidden (e.g., "Do not use library X because of security vulnerability Y").
- Link to troubleshooting guides for deeper dives.

## 6. Plan-Validate-Execute Loops

- Instruct the agent to create a plan first.
- Provide validation scripts to check work before "committing" (e.g., linting, type-checking, or running a validator).
