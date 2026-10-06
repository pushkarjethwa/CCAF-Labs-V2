# Lab 1A - Model tournament (run it yourself)

**Time:** 60-75 min if you run everything | **Needs API key** | **Cost:** about $0.5-1 for stages 1-5 (stage 4 `--sweep` adds about $2) | **Exam:** D4 Prompt and Structured Output, model selection and cost

This is the self-contained, run-it-yourself version of the trainer's Day 1 Demo 1A. There are no TODOs. Every stage is finished code that you run, then read, then change (see BREAK_IT).

## Story
Larkspur Components (fictional) must label every inbound invoice **low / medium / high / hold** before money moves, for 100,000 records. A rules engine gets 12 of 24 labelled test invoices right. The 24 cases include the ones that cost real money: a changed bank account, a duplicate invoice number, an amount just under the approval limit, a look-alike vendor name.

**The question:** which Claude model should do this? The answer is measured, and it is usually an architecture, not the biggest model.

## Stages (run in order)
| Stage | Command | What you learn |
|---|---|---|
| 0 | `python demo.py --stage 0` | The "before": dataset, scorer, rules engine, price table. No Claude call, free |
| 1 | `python demo.py --stage 1` | One hard case, three models, plain text. Tiers may disagree, and free text is not a contract |
| 2 | `python demo.py --stage 2` | Strict JSON schema output plus a validator. Parameter traps: `temperature` and forced `tool_choice` are rejected on newer models |
| 3 | `python demo.py --stage 3` | The tournament: 24 cases x 3 models. Quality, cost, speed, misses, confidence intervals |
| 4 | `python demo.py --stage 4` | Cheap-first routing, the blind spot of confidence, and a constraint-driven recommendation for 100k records |
| 5 | `python demo.py --stage 5` | A hardened router: outages never crash it, failures never relax a hold, every decision is logged |
| - | `python demo.py --stage failures` | Ten bad outputs and what the validator says. Free |

Add `--limit 8` to any stage to use only the first 8 cases. Run `python check.py` after stages.

## Files
| File | What it is |
|---|---|
| `demo.py` | All stages. Parts A-D are in reading order: ledger, output contract, one classification, stages |
| `ap_data.py` | Given: dataset loader, case view, scorer, legacy rules. Read it, do not edit |
| `claude_client.py` | The only file that talks to Claude (read it once) |
| `data/` | Invoices, vendors, payment history, policy, ground truth (never shown to a model), routing policy, bad outputs |
| `check.py` | Part A (no key): plumbing and validator. Part B: sanity checks on your evidence |
| `evidence/` | Created by the stages |

## Setup and run
```
pip install -r requirements.txt
python demo.py --stage 0
python demo.py --stage 1
...
python check.py
```

## Honest notes
- 24 cases is a tiny sample. Look at the confidence intervals; one case is not evidence. Run stage 3 twice and compare.
- Fast-tier behaviour on the bank-change invoice (inv_017) is a tendency, not a guarantee. Report what you see.
- Model names and some API rules change. If a call fails with "model not found", set `CLAUDE_MODEL_FAST` (or `_BALANCED`, `_PREMIUM`). The error demos in stage 2 show what YOUR models accept today.
- `check.py` verifies the demo ran sensibly. It does not grade model quality.
- This version has not yet been run against the live API; tell your trainer if a stage fails.
