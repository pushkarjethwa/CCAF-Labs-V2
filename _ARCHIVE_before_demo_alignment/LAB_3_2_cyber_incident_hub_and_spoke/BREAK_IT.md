# Break it (after check.py is green)

Change one thing, run `python lab.py` and `python check.py`, predict first, then note which check caught it and what real incident it predicts. Undo after each.

1. **"Just a little context."** Add `"history": json.dumps(incident)` (no private data) to the triage brief. Does the leak test catch it? Does anything? Which check does? (Lesson: least privilege is checked on fields, secrets on terms.)
2. **Forward private notes by mistake.** Add `PRIVATE["note"]` to one brief. What is the smallest change that makes the leak test fail? What did the real Claude analyst do with it?
3. **Unbounded rework.** Set `MAX_REWORK = 50`. Which scenario changes and what does `runtime_calls` show? What would it cost with a real model call per attempt?
4. **Swallow a failure.** Make `delegate_rule` return `"retry"` for an unavailable specialist forever. What stops it? (Hint: `RUNAWAY_LIMIT`. Why must that be a last resort and not your policy?)
5. **Make threat_intel essential.** Add `"threat_intel"` to the containment list in `NEEDS`. What does S2 do to the plan? Is an intel outage a good reason to stop containing an attack? Argue both sides.
6. **Skip the approval rule.** Remove the high-risk rule from `semantic_problems` and force a plan with a high-risk action and `requires_approval` false. What stops an unapproved isolation now? Where should the second line of defence live?
