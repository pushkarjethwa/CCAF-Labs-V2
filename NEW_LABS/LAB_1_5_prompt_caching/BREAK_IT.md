# Break it - Lab 1.5
1. **Haiku floor.** Set `CLAUDE_MODEL_BALANCED` to your Haiku model and run again with the policy cut to 2,000 words. `cache_write` stays 0 with no error. Silent failure: why is that dangerous for a cost saving you planned on?
2. **One character.** In the cached run, add a changing character to the START of the instructions (such as a counter). Cache reads go to 0.
3. **Wrong place.** Put `cache_control` on the small second block only. What gets cached?
4. **Expired cache.** Wait 6 minutes between two calls. Read the first call's numbers.
