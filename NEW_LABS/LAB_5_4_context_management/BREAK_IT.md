# Break it - Lab 5.4
1. **Drop instead of compact.** Make `compact` delete old messages. Run: the cost falls, and the answer about report 2 is wrong or invented. Compare the two answers.
2. **Keep the wrong line.** Keep the LAST line of each report instead of the first. What does Claude say about report 2 now?
3. **Break alternation.** Delete a message so two user messages are adjacent. Read what the API does.
4. **Compact the newest turn.** Set `KEEP_LAST = 0`. What happens to the answer to the final question?
