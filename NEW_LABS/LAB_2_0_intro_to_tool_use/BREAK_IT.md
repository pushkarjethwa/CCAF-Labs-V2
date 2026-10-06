# Break it - Lab 2.0
1. **Vague description.** Change both descriptions to "Look something up." and run step 3. Does Claude still pick correctly?
2. **Wrong id.** In step 2D change `tool_use_id` to `"abc"`. Read the 400 error: every tool_use needs a matching tool_result.
3. **Skip the result.** Remove the tool_result message in step 2D. What does the API say?
4. **Invent data.** Remove the order tool in step 2 but keep the system prompt. Does Claude still refuse to invent the carrier?
