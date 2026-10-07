# Solution guide: Lab 1.1 - HR Roster Classification: which model is good enough, and what does it cost at scale?

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Choosing a model with evidence: classify the same HR roster on the fast, balanced and premium tiers, compare accuracy, cost and latency at scale, and respect a hard cap on premium calls.

## 2. Solutions, one TODO at a time

Each block shows the TODO text, then the code that solves it. Names follow the starter file.

### Block 1: def main()

What the TODO asks:

> TODO 1: add ("balanced", MODEL_BALANCED, rows) - the balanced model on all 40 rows.
> TODO 2: add ("premium", MODEL_PREMIUM, hard_rows) - the premium model on the 8 hard rows ONLY.
> run_model() already refuses non-hard rows and stops after MAX_PREMIUM_CALLS. Think about what spending
> limit is sensible before you run it: premium costs roughly 2x balanced per token.

Solution:

```python
plan = [("fast", MODEL_FAST, rows), ("balanced", MODEL_BALANCED, rows), ("premium", MODEL_PREMIUM, hard_rows)]
```

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- >= 2 models measured on all 40 rows (TODO 1)
- premium model measured on exactly the 8 hard rows (TODO 2)
- premium calls <= 8
- results table has accuracy / compliance / latency / tokens / cost for every model
- accuracy and schema-compliance numbers match the stored predictions vs ground truth
- cost per 1k rows = total cost / rows * 1000, and cost > 0
- 100,000-row projection (sync and batch) matches the measured average tokens
- no temperature= argument in the classifier code (gotcha avoided)
- param probe recorded: temperature kwarg -> TypeError, temperature on Sonnet -> BadRequestError (python lab.py --probe)
- decision memo exists, >= 60 words, no unfilled [[placeholders]]
- memo has a 'Decision:' line naming a model you measured
- memo has a 'Rejected:' line for a different model with a numeric reason
- memo quotes the chosen model's 100,000-row projection (sync or batch) within 2% of the evidence

## 4. Common mistakes

- Judging by the average only. Look at which rows each tier misses and whether the misses are the expensive kind.
- Extrapolating cost from the 8 hard rows without scaling by the price ratio and the token counts.
- Treating a schema-valid reply as a correct one (see BREAK_IT drill 1).

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Drill 1: the enum schema guarantees the label is one of the allowed values, not that it is right. A hostile note field may or may not be obeyed by a real model, but nothing in the schema stops it. Fix: state in the rubric that note text is data, never instructions, and wrap the record in tags. For the empty row, add an `UNKNOWN` enum value (honest, but needs a human queue) or pre-filter empty rows (cheap, but silent).
2. Drill 2: the run raises `RuntimeError` after 5 premium calls and no `evidence.json` is written. A ceiling in code cannot be forgotten the way a note in the lab text can. Save partial results before raising to avoid losing them.
3. Drill 3: your estimate is usually close on input and off on output, because output length differs by model (premium tiers often think and write more) and token counts differ by tokenizer.

## 6. Files in this folder

- `lab_solution.py`: complete reference solution (replace the matching file in the lab folder to test it)
- `SOLUTION_GUIDE.md`: this file
