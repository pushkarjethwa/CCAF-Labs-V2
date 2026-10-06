# Break it - Lab 1A
1. **Trust the confident wrong answer.** In stage 4 set `RoutePolicy.high_value_usd` to a huge number. Which case now slips through the router with a confident wrong label?
2. **Drop the semantic validator.** In `check_output`, accept confidence 95. Run `--stage failures` and stage 3. Which downstream rule would break?
3. **Crown the expensive model.** Change `recommend()` to pick the highest accuracy. What does the recommendation cost per 100k, and was the extra accuracy more than one case?
4. **Send temperature.** Add `temperature=0` to `ask()` in `claude_client.py` and run stage 3. Read the error. How would you find out which models still accept it?
5. **Starve the thinking budget.** Set `max_tokens=300` in `classify()`. Check `stop_reason` and the Table 4 glitches.
6. **Trust one run.** Run stage 3 three times. Which numbers move? What does that say about a 24-case benchmark?
