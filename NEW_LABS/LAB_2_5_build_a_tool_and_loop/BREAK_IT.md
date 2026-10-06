# Break it - Lab 2.5
1. **Vague description.** Change both descriptions to "Look something up." Run `lab.py`. Does Claude still pick correctly? Try the "needs both" question.
2. **Wrong id.** In the loop, send the tool_result with a made-up `tool_use_id`. Expect a 400 error from the API. Read the message.
3. **Split results.** For the "needs both" question send each tool_result as its own user message. Read the error.
4. **No exit.** Set `MAX_TURNS = 100` and make a tool always return an error. How many calls does it make before it stops, and what does that cost?
