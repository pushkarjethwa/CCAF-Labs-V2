# Solution guide: Lab 1A - Model tournament (run it yourself)

> **Spoiler warning.** Try the lab yourself first, using `README.md`, the TODO comments and `check.py`. Open this guide when you are stuck, or after you finish to compare. Your solution does not have to match line for line: if `check.py` passes and you can explain why, it is correct.

## 1. What this lab teaches

Choosing a model by measurement: plain text vs structured output, parameter traps, a 24-case tournament with confidence intervals, cheap-first routing, and a constraint-driven recommendation for 100,000 records.

## 2. Answer key for the run-it-yourself stages

This lab has no TODOs: you run stages and read results. These are the answers to the PREDICT prompts and what the output should show. Your numbers will differ run to run and by model version; the shape should match.

- Stage 1 predict: tiers can disagree on inv_017 (bank change by email, truth `hold`); the naive script reads the first label word, so it often returns `low` even when the model said `hold` ('not a routine low or medium item').
- Stage 2: all three tiers return schema-valid JSON. `temperature` kwarg: TypeError. `extra_body` temperature and forced `tool_choice`: HTTP 400 on newer tiers (what your models do today is what you record).
- Stage 3: typical shape: premium costs several times more than fast for a few extra correct cases; Table 4 shows glitches the schema cannot forbid (confidence outside 0..1, empty reasons, capitalised labels).
- Stage 4: most easy cases stay on the fast tier; high-value and low-confidence cases go to balanced; premium only sees `hold` disagreements. The recommendation is the cheapest strategy that meets 'hold recall 100% and weighted error 0': often the routed cascade, not the biggest model.
- Stage 5: a tier outage or refusal never crashes the run; with no usable answer the case goes to a human with the riskiest usable label, so a failure can never relax a hold.

## 3. What a passing `check.py` looks like

`check.py` runs these checks (descriptions as printed). Part A needs no API key; Part B reads the evidence from your live run.

- 24 invoices, each with a ground-truth label
- legacy rules engine: 12/24 correct, hold recall 1/5
- the case view never contains the ground-truth rationale
- with n=24 the 95% interval is wide (that is the lesson)
- validator agrees with all 10 bad-output cases (incl. confidence 95 and empty reasons)
- a schema-valid answer can still be unusable (confidence 95)
- stage 1: all three tiers answered in plain text
- stage 2: all three tiers returned schema-valid JSON
- stage 2: temperature kwarg raised TypeError in the SDK
- stage 3: every tier classified every case
- stage 3: at least 90% of answers were schema-valid on every tier
- stage 3: cost per 100k rises fast < balanced < premium
- stage 4: routed cascade and Haiku-only strategies were compared
- stage 4: premium sees no more cases than balanced, which sees no more than all
- stage 5: every case was routed to a queue and logged
- stage 5: a case with no usable answer always goes to a human

## 4. Common mistakes

- Reading accuracy alone. The cost of a missed `hold` is far higher than an over-flag: read hold recall and weighted error.
- Believing a difference of one case on 24 is real (the Wilson intervals overlap heavily).
- Routing on confidence alone: a model can be confidently wrong (look for the BLIND SPOT line); the high-value rule is what catches it.
- Sending `temperature` or a forced `tool_choice` to newer models.

## 5. Answers to BREAK_IT

Same order as `BREAK_IT.md`. Results from live models vary: if yours differs, note it and explain why; that is the exercise.

1. Raising `high_value_usd` to a huge number removes the rule that catches confident wrong answers: expect a high-value duplicate-invoice case (for example inv_018) to slip through the router.
2. Accepting confidence 95 makes the validator pass a number that is not a probability; a downstream threshold such as `confidence < 0.75` would then never escalate.
3. Picking the highest accuracy usually crowns the most expensive model for at most a case or two: the recommendation costs several times more per 100k for no measurable gain on 24 cases.
4. `temperature=0` raises `TypeError` in the SDK; through `extra_body` newer models answer HTTP 400. Check which models still accept it, or simply never send it.
5. `max_tokens=300` starves the hidden thinking budget on 5.5-generation models: `stop_reason == 'max_tokens'` and truncated or empty text show up as unusable outputs in Table 4.
6. Running stage 3 three times moves accuracy by a case or two and latency a lot: a 24-case benchmark gives a direction, not a verdict.

## 6. Files in this folder

- `SOLUTION_GUIDE.md`: this file
