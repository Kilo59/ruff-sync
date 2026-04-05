# Optimizing Skill Descriptions

The `description` field in a Skill's frontmatter determines *if* the agent chooses to use the skill.

## 1. Writing Effective Descriptions

- **Imperative Phrase**: Use "Use this skill when..." rather than "This skill does...".
- **Focus on User Intent**: Describe what the user wants to achieve (e.g., "Analyze CSVs") rather than internal mechanics ("Run `scripts/csv_parser.py`").
- **Err on the Side of Being Pushy**: Explicitly list contexts where the skill applies, including synonyms (e.g., "even if they don't explicitly mention 'CSV' or 'analysis'").
- **Concise & Goal-Oriented**: A short paragraph (<1024 chars) is usually right.

## 2. Avoiding Overfitting

- **Broaden the Scope**: If you miss a "should-trigger" case, broaden the description.
- **Avoid Keyword Stuffing**: Don't just add words from failed queries. Identify the *general category* those words represent.
- **Structural Changes**: If tweaks fail, try a different framing or sentence structure.

## 3. Testing with Queries

- **Should-Trigger Queries**: Test with formal, casual, and typo-ridden prompts.
- **Should-Not-Trigger Queries**: Test with "near-misses" (e.g., "I need to edit Excel budget" vs "I need to analyze CSV sales").
- **Validation Pass Rate**: Use fresh queries (not the ones used to train/optimize) to check for generalization.

## Checklist for Activation

- [ ] Is it under 1024 characters? (Hard limit)
- [ ] Does it start with "Use this skill when..."?
- [ ] Does it cover at least 3-4 likely phrasing variations?
- [ ] Is it separate from other skills in the same repository? (Avoid overlap)
