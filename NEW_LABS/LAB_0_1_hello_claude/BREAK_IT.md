# BREAK IT - Lab 0.1

Change one thing at a time in `lab.py`, run, and write down what happens.

1. Remove `system=SYSTEM` in step 1. How does the answer change?
2. In step 2, leave out the assistant message (send two user messages in a row). Does Claude understand "I already restarted it"?
3. Pass `max_tokens=0` in step 3. What error do you get, and which exception class is it?
4. Rename your model to `claude-sonnet-9` with `set CLAUDE_MODEL_BALANCED=claude-sonnet-9`. Which exception appears (NotFoundError)?
5. Pass `temperature=0` to `ask()` in step 1. What happens, and why does the comment in `claude_client.py` warn about it?
