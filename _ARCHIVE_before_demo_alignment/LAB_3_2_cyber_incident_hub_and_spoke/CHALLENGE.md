# Challenges (optional)

1. **Second real spoke.** Replace the scripted threat_intel with a Claude call. What new failure can it have that the scripted one could not (an invented campaign name)? Which contract rule would catch it?
2. **Parallel spokes.** threat_intel and triage do not depend on each other. Run them concurrently. What happens to the trace and the retry accounting?
3. **Output filter.** Add a last-line scan of the final summary for private terms. Why is a filter a second control and not a replacement for least-privilege briefs?
