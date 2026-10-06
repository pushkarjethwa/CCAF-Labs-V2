# Challenge - Lab 2.5
1. Add a third tool `reserve_book(title, member_id)` that changes state. Decide: how do you stop Claude from reserving twice (hint: idempotency key)?
2. Replace your hand-written loop with the SDK tool runner (`client.beta.messages.tool_runner`) and compare the code size.
3. Print `usage` for each turn and explain why total input tokens grow with every turn.
