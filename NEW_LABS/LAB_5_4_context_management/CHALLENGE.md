# Challenge - Lab 5.4
1. Replace the estimate with the real count: `client.messages.count_tokens(...)`. How far off was 4 characters per token?
2. Instead of first-line-only, ask Claude to summarise each old report in one sentence (a second, cheap model call). What does that cost, and does it beat the first line?
3. Move the findings into a pinned "facts so far" block in the system prompt that you update each turn, and drop the old messages entirely.
