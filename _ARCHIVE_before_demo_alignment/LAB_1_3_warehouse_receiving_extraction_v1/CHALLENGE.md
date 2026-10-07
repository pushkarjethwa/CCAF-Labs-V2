# Challenge - Cumulative receipts and partial shipments

Today every email is judged against the **full** ordered quantity. Real POs are received in several shipments (GR-008 and GR-012 are both deliveries against PO-48207).

Extend the system so that:
1. A receipt ledger (a JSON file you create) accumulates `qty_received` per PO line in PO units across accepted emails.
2. `short` means "less than ordered **so far**" and a later shipment that completes the line clears the shortage, while exceeding the ordered total (cumulatively) is `over`.
3. Email order must not matter for the final totals - prove it by processing the 20 emails in two different orders.
4. A failed (needs_review) email must not touch the ledger.
5. Report: for each PO, ordered vs received-to-date and which lines still need follow-up.

Design questions to answer in writing: where does the ledger update happen relative to validation, and what happens if the process crashes between acceptance and ledger write? How would you make the update idempotent if the same email is delivered twice?

Success criteria are yours to define; list at least three tests, one of which uses a duplicated email. No reference solution is provided.
