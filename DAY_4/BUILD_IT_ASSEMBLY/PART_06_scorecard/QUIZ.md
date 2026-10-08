# Day 4 Build-It quiz (topics 16 to 20)

Ten questions. One answer is correct. The answer key is at the end.

### Question 1

Which question is best answered with a content search (grep) and not a file-name search (glob)?

- A. Which files in the repository are tests?
- B. Where in the code are points rounded?
- C. Which folders contain Python files?
- D. What are the names of the markdown files in docs?

### Question 2

The team never wants an `bb_live_` key written into source. Which choice enforces that rule, instead of only asking for it?

- A. A line in CLAUDE.md that says never write bb_live_ keys.
- B. A skill with a description that mentions secrets.
- C. A PreToolUse hook that exits with code 2 when the edit contains an `bb_live_` key.
- D. A longer prompt at the start of every session.

### Question 3

You want private notes about this project that must not be committed or shared with the team. Where do they go?

- A. The CLAUDE.md in the repository root.
- B. CLAUDE.local.md in the repository root, kept out of git.
- C. The managed policy file.
- D. src/rewards/CLAUDE.md.

### Question 4

A rule file in .claude/rules has `paths: ["src/rewards/points.py"]` in its front matter. When does Claude load the rule?

- A. At the start of every session, whatever the work.
- B. Only when you run `/memory`.
- C. When Claude works on a file that matches the pattern.
- D. Only when a hook asks for it.

### Question 5

A skill sets `context: fork`. What is the effect?

- A. The skill runs in a separate context, and the main conversation receives the result.
- B. The skill copies the repository into a new branch.
- C. The skill runs on every file change.
- D. The skill is shared with every user on the machine.

### Question 6

You want every teammate who clones the repository to get the menu MCP server. Which scope do you use?

- A. Local scope, which is private to you in this project.
- B. User scope, which applies to all your projects on your machine.
- C. Project scope, which is stored in .mcp.json and committed.
- D. No scope. Servers cannot be shared.

### Question 7

You closed a long session yesterday. Which command continues the most recent conversation in this folder?

- A. `claude -c`
- B. `claude --bare`
- C. `claude --fork-session`
- D. `claude -p`

### Question 8

A CI job needs Claude's review as data that a script can check. Which flags give a JSON envelope with the findings in a validated shape?

- A. `-p` with `--allowedTools`.
- B. `--bare` with `--max-turns`.
- C. `--tools ""` with `--max-budget-usd`.
- D. `-p` with `--output-format json` and `--json-schema`.

### Question 9

Why does the review workflow use the `pull_request` event and not `pull_request_target`?

- A. `pull_request_target` cannot post comments.
- B. `pull_request_target` runs with the secrets and write token of the base repository, so untrusted pull request code could misuse them.
- C. `pull_request` is faster.
- D. `pull_request_target` only works on forks.

### Question 10

The gate exits with code 3. What does that mean?

- A. A blocker was found and the pull request must not merge.
- B. The change passed.
- C. The review answer was not valid structured findings.
- D. The result was inconclusive because no review was produced, so the job must not pass quietly.

## Answer key

1. B. Finding where something is done means searching inside files, which is grep. The other questions are about file names.
2. C. A hook runs before the edit and blocks it, while the other choices are advice that Claude may not follow.
3. B. CLAUDE.local.md holds private project notes and stays out of git.
4. C. Path-scoped rules load when Claude touches a matching file, which keeps the context small.
5. A. A forked skill runs in its own context and hands back its result.
6. C. Project scope writes to .mcp.json, which is committed, so teammates get the server.
7. A. `claude -c` continues the most recent conversation in the current folder.
8. D. `--output-format json` gives the envelope and `--json-schema` gives validated findings in `structured_output`.
9. B. `pull_request_target` gives the workflow secrets and write access, so it is dangerous to combine with untrusted code.
10. D. Exit 3 means inconclusive: there was no usable review, and the gate does not pass in silence.
