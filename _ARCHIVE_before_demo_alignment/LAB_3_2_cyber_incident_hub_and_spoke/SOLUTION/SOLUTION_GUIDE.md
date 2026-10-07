# Lab 3.2 solution guide

The full working file is `lab_solution.py` (same folder).

| TODO | Decision | Why |
|---|---|---|
| 1 `FIELDS` | log_analysis: timeline list, suspicious_ips list, compromised_accounts list; threat_intel: matches list; containment_plan: actions list, requires_approval bool | A shape contract catches missing fields and wrong types before the next specialist trusts them |
| 2 `semantic_problems` | wrong incident_id; reputation outside the allowed set; high-risk action without `requires_approval` | A schema cannot express "true"; these are truth rules |
| 3 `correction` | `"CORRECTION: ..."` plus every problem | The specialist (and the fault injector) can only fix what it is told, exactly |
| 4 `brief_for` | only the fields each specialist needs; indicators and accounts come from the earlier hand-offs | Least privilege: private data cannot leak through a brief that never contains it. The hub does no analysis itself |
| 5 `delegate_rule` | malformed: rework while `tries <= 1`; unavailable: retry while `tries <= 1`; then give up | Two failure classes, two policies, both bounded |
| 6 `NEEDS` | threat_intel needs log_analysis; containment needs triage and log_analysis | Intel is nice to have; losing it must not stop containment (S2 stays `partial`) |

## Why the table comes out as it does

- S2: one retry fails too, so threat_intel is recorded as an environment failure. Nothing needed it, so containment runs on log_analysis' addresses. The hub says `partial` and flags a human.
- S3: the first log_analysis answer is rejected (shape), the correction goes back, the second is clean: `complete` with one rejection and two calls.
- S4: the rework is rejected as well. log_analysis is needed by threat_intel and containment, so both are skipped: `failed`, a human is flagged, no downstream calls.

## Common mistakes

- Leaving `"history"` in a brief "just for context".
- Computing the suspicious IPs in the hub (a regex over the logs): domain work in the coordinator.
- `tries < MAX_REWORK` instead of `<=` (no rework at all).
- A `correction` message that does not start with CORRECTION.
