# Evaluating Skill Quality

"Eval-driven iteration" is the process of testing your skill against realistic prompts to ensure it produces high-quality, reliable outputs.

## 1. Designing Test Cases

A good test case includes:
- **Prompt**: A realistic user message (e.g., "Analyze the CSV at data/sales.csv").
- **Expected Output**: A human-readable description of success.
- **Input Files**: Mock data or real project files needed for the task.
- **Assertions**: Specific, observable criteria for success.

### Example Eval (evals.json)
```json
{
  "id": 1,
  "prompt": "Summarize the linting errors in src/core.py",
  "expected_output": "A markdown table with Error Code, Message, and Line Number.",
  "assertions": [
    "Output is a markdown table",
    "Includes at least 3 columns",
    "All error codes start with 'E' or 'W'"
  ]
}
```

## 2. Running Evals

**The Loop**:
1. **Baseline**: Run the prompt *without* the new skill instructions.
2. **With Skill**: Run same prompt with the skill active.
3. **Compare**: Measure the delta in quality, time, and tokens.

**Workspace Structure**:
Store iteration results in separate folders (e.g., `iteration-1/with_skill/outputs/`) to track progress over time.

## 3. Grading with Assertions

- **Programmatic**: "Output is valid JSON."
- **Observable**: "The chart has labeled axes."
- **Countable**: "Includes at least 3 recommendations."

**Grading Principle**: Require concrete evidence for a PASS. If it's vague, it's a FAIL.

## 4. Analyzing Patterns

- **High StdDev**: If results vary wildly across runs, the instructions may be too ambiguous.
- **Plateau**: If more rules don't improve the pass rate, the skill may be over-constrained. Try simplifying.
- **Delta**: Focus on where the skill actually changes the agent's behavior compared to the baseline.
