# Lab 3.1 - Product recall: choose the architecture (about 25 minutes)

Halvorsen Home Appliances is recalling a kettle line. You make two sets of decisions, as two small tables. **No JSON, no schema, no code to write.** You fill in rows.

1. **Table 1 - four briefs:** is each one *conversational*, *workflow* or *agentic*? The deciding question is **who controls the next step**.
2. **Table 2 - seven recall steps:** is each an *agent*, a *tool* or a *fixed step*? Use the least power that works. Say how you would test each one.

The rules and a real Claude critique are provided.

## Set up

```
pip install -r requirements.txt
```

Put `ANTHROPIC_API_KEY=...` in a `.env` file next to `lab.py` (only needed for Step 4).

## Your files

| File | What it is |
|---|---|
| `lab.py` | The only file you edit. Sections 1 and 2 are your tables. Section 3 is plumbing: do not edit. |
| `check.py` | Plain-words pass/fail. The rules part needs no key. |
| `data.json`, `claude_client.py` | The scenario and the Claude helper. Leave alone. |

## Steps

1. `python lab.py --show` prints the four briefs and the seven steps with their **facts**. Decide from the facts, not from intuition.
2. Run `python lab.py` once to see what the rules say about the naive starter ("everything is an agent").
3. Fill in Table 1 (4 rows), then Table 2 (7 rows) and the one data-flow pick. Run `python check.py` often; each row turns green when its rules pass.
4. When all rules pass, `python lab.py` asks Claude for a second opinion on your design (one real call). Read what it names as your weakest pick and decide whether you agree.
5. `python check.py` ends with `RESULT: 16/16 checks passed`. Then try `BREAK_IT.md`.

## Vocabulary

| Word | Meaning |
|---|---|
| agent | a model chooses its own next action in a loop, because the path cannot be written in advance |
| tool | deterministic, typed, no model decisions |
| fixed step | position and logic fixed in code; may contain at most one scripted model call |

At most **2 agents** are allowed.

## Stuck?

Each failing line says which rule fired and what to look at. Last resort: `SOLUTION/SOLUTION_GUIDE.md`.
