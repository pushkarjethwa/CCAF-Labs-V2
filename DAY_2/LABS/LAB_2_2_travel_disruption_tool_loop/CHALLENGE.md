# Challenge - Lab 2.2 (open-ended, no solution code provided)

**Three travelers, one cancelled flight.** `DATA/scenario.json` lists three affected PNRs (T-1001 Gold, T-1002 Silver, T-1003 Basic) but only 3 seats on OPT-B and a hotel with 4 rooms. Extend the system so all three are handled in one run.

Requirements (you decide the design):
1. Reads that are shared (flight status, options, hotels) happen **once**; per-traveler reads (loyalty tier) run concurrently.
2. Per-traveler chains (rebook -> hotel -> notify) are independent of each other. Decide whether different travelers' chains may run in parallel, and what shared resource (seats, rooms) makes that unsafe or safe. Defend your choice in writing.
3. Seats and rooms are limited: define what happens when a traveler's preferred option sold out between read and write (hint: the error type matters - is it retryable?).
4. Extend `check.py`-style assertions in your own `my_checks.py`: no seat oversold, every ledger entry verified, ordering per traveler, total elapsed time lower than fully sequential.
5. Stretch: add a per-conversation budget (max tool calls) and report it as `stopped="budget"` distinct from `max_turns`.

Deliverable: your modified code, `my_checks.py` output, and 5 lines on the trade-off you made.
