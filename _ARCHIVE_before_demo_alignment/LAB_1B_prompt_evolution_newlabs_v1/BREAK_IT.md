# Break it - Lab 1B
1. **Edit a released prompt.** Add one space to `prompts/v6.md` and run `python demo.py --stage vault`. Read the failure. Why is a silent prompt edit a production change? Restore the file (or run `python -c "from vault import Vault; Vault().lock()"` only after review).
2. **Trust the average.** After stage 3, compare the headline accuracy of v3 and v4 with the per-document table. Could you have shipped v4 on the average alone?
3. **Anti-copy sentence only.** In stage 4, does `v4+rule7` still leak? Remove the near-duplicate example from `v4.md` yourself (new file `v4b.md`) and compare.
4. **Drop the XML.** Run stage 5 and compare `v6_no_xml` with `v6` on D11. If both pass, write your own harsher embedded instruction into a copy of `data/docs/D11.txt` and try again.
5. **Strict vs loose.** Change the scorer's parse so only strict `json.loads` counts. Which versions collapse?
6. **A schema the API rejects.** Add `"minimum": 0` to `total` in `prompts/schema_invoice.json` and run stage 5. Read the error, then run `kit.audit` on the schema to see it flagged before the call.
7. **Write a bad candidate.** Create `candidates/v7_mine.md` that removes the credit-note rule, add it to `GATE_CASES`, and see which gate check catches it.
