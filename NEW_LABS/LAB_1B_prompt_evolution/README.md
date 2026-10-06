# Lab 1B - Prompt evolution (run it yourself)

**Time:** 60-75 min if you run everything | **Needs API key** | **Cost:** roughly $1-2 for stages 1-6 plus the gate | **Exam:** D4 Prompt Engineering and Structured Output

This is the self-contained, run-it-yourself version of the trainer's Day 1 Demo 1B. There are no TODOs: each stage is finished code that you run, read, then change (see BREAK_IT).

## Story
An accounts-payable team receives vendor invoices as messy OCR-style text: mixed date formats (`03.04.2025`, `5 mars 2025`), `$` that means several currencies, European decimal commas (`2.598,37`), two-page invoices, credit notes, blank PO lines, OCR typos, and one invoice that contains a sentence addressed to "automated systems". A legacy regex extractor scores about 42%. You take a one-line prompt (`v0: "Extract the invoice."`) through seven versions, and at every step you **RUN -> MEASURE -> COMPARE** on the same 12 invoices with a field-level scorer.

**The point:** prompts are production code that nobody reviews. The usual failure is not "the model is bad": nobody measured, so nobody noticed that a clever edit made one kind of document worse. The lab ends with the artefact that stops that: a versioned, hash-locked prompt vault and a regression gate.

## Stages (run in order)
| Stage | Command | Versions | What you learn |
|---|---|---|---|
| 0 | `python demo.py --stage 0` | legacy | The bar to beat. No Claude call, free |
| 1 | `python demo.py --stage 1` | v0, v1 | A one-liner returns prose the system cannot parse; a role is not a contract |
| 2 | `python demo.py --stage 2` | v2, v3 | Explicit per-field criteria, then an output-format contract; strict vs loose parsing |
| 3 | `python demo.py --stage 3` | v4 | Few-shot examples help format but can LEAK values into similar documents; an average hides it |
| 4 | `python demo.py --stage 4` | v5 | Edge-case rules; an anti-copy sentence alone does not remove the leak |
| 5 | `python demo.py --stage 5` | v6 | JSON schema through `output_config.format`, XML separation, the embedded-instruction trap |
| 6 | `python demo.py --stage 6` | v6 | Fast vs balanced model, cost per 10,000 documents, caching and batch, validator-gated cascade, decision |
| - | `python demo.py --stage vault` | all | Prompt vault: versions, lineage, sha256 verification. Free |
| - | `python demo.py --stage gate` | v6 + 3 candidates | Regression gate: which prompt edits may be promoted |

Run `python check.py` after the stages.

## Files
| File | What it is |
|---|---|
| `demo.py` | All stages. Part A (run one version and score it) is the engine; Part B holds the stages |
| `evalkit.py` | Given: docs, parsing, prompt files, scorer, leak check, semantic checks, schema audit, report tables. Read it, do not edit |
| `vault.py` | Given: the hash-locked vault and the regression gate |
| `legacy_extractor.py` | The regex baseline (no Claude) |
| `claude_client.py` | The only file that talks to Claude (read it once) |
| `prompts/` | `v0.md` ... `v6.md`, an ablation, the JSON schema, `vault.json`, `vault.lock.json` |
| `candidates/` | Three "v7" edits that the gate judges |
| `data/` | 12 invoice texts, ground truth, few-shot example material; `DATA_NOTES.md` says what each document tests |
| `check.py` | Part A (no key): scorer, validators, schema audit, vault tamper test. Part B: sanity checks on your evidence |

## Setup and run
```
pip install -r requirements.txt
python demo.py --stage 0
python demo.py --stage 1
...
python check.py
```

## Honest notes
- Strong models may do better than the prompts' "designed" failures suggest: v0 may parse, the leak may not appear, the D11 note may be ignored. That is a finding, not a bug. Report what you see, and run a stage twice.
- 12 documents is a small sample: one wrong field is 0.83 points of accuracy.
- The gate's thresholds (1 point overall, 5 points per field, 1 document, 0 leaks) are in `vault.py`. Real models may pass or fail the three candidates differently from the designed verdicts.
- `check.py` verifies the lab ran sensibly. It does not grade model quality.
- This version has not yet been run against the live API; tell your trainer if a stage fails.

## Stuck?
Try the lab first. If you need a hint or want to compare, open `SOLUTION/SOLUTION_GUIDE.md` (solutions, expected results, answers to BREAK_IT).
