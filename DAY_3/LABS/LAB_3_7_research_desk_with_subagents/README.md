---
lab:
    title: 'Build the Research Desk as a Multi-Agent System'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build the Research Desk as a Multi-Agent System

In Demo 3G, you watched the final design of the research desk written with the Claude Agent SDK. A coordinator delegates each question to four specialists: a searcher, an analyst, a fact-checker, and a writer. The coordinator holds a confidential client note and never researches anything itself. Three controls made the desk safe: each specialist has only the tools its job needs, a hook blocks any brief that contains the confidential note, and a conflict between reliable sources goes to a human. In this lab, you write those controls yourself, for the same desk, with the same corpus and the same questions.

You will complete three pieces of **lab.py**, which add up to 39 lines of code. The lab takes about 40 minutes, and this guide gives you every line. At the end, the desk answers two real questions, and a scorer checks the answers against the ground truth.

This lab continues Demo 3G, so you will recognize the following:

- The research desk, its 40-document corpus, its five tools, and the confidential client note about Pallo Systems.
- The coordinator and the four specialists, with the searcher and the writer already written for you.
- The three controls: least privilege, context isolation with a PreToolUse hook, and escalation.
- The questions Q2 (two reliable reports disagree) and Q5 (a rumour sits next to the confidential note), and the string-matching scorer.

## Set up the lab folder

> **Note**: This lab needs two things from **DAY_0_SETUP_GUIDE.md**: the `claude-agent-sdk` package (section 3) and the Claude Code command-line tool (section 8). If either is missing, finish that part of the Day 0 guide first.

You need Python 3.10 or later, an Anthropic API key, and the Claude Code command-line tool, because the Agent SDK runs it as a helper process.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_7_research_desk_with_subagents** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Verify that the Claude Code command-line tool is installed by running the following command:

    ```
    claude --version
    ```

    > **Note**: If the command is not found, ask your instructor to help you install Claude Code. The SDK uses your API key. Do not sign in with a claude.ai account.

4. Create a new file named **.env** in the lab folder, and add the following line, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

## Review the starting point

1. Run the checker by running the following command:

    ```
    python check.py
    ```

    > **Note**: The checker fails on purpose. Part A tests your three TODOs with no API key and no model. Part B is skipped until you run the desk.

2. Notice that only two files matter for this lab: **lab.py**, which holds your three TODOs, and **check.py**. The **research_tools.py** file holds the five tools and the corpus, and you do not need to read it.

3. Open **lab.py** and read the comment block at the top of the file, noting the following details:

    - The coordinator delegates and never researches.
    - The searcher and the writer are already written, so you can see what a finished specialist looks like.
    - The starter versions of the analyst and the fact-checker can use every tool, which is the problem you fix first.

## Give each specialist only the tools it needs

Least privilege means that a specialist cannot misuse a tool it does not have. The analyst only needs arithmetic. The fact-checker only needs to re-read documents.

1. In **lab.py**, search for the comment **TODO 1 of 3 - SUBAGENTS**. Below it is the `SUBAGENTS = {` dictionary, with the searcher already written.

2. Find the two entries that start with `"analyst"` and `"fact_checker"`, which sit between the searcher and the writer. Each has a short placeholder description and every tool.

3. Select both entries, and replace them with the following code:

    ```python
        "analyst": AgentDefinition(
            description="Does exact arithmetic (CAGR, per-unit prices, ratios) on numbers it is given.",
            prompt="You calculate. Use the tools for every number you report; never do arithmetic in your head. "
                   "Reply with each result and the inputs you used.",
            tools=[mcp("cagr"), mcp("divide")],
            maxTurns=6,
        ),
        "fact_checker": AgentDefinition(
            description="Re-reads cited documents and checks that each claim is supported. Flags conflicts between sources.",
            prompt="You verify claims. For each claim and doc_id you are given, fetch the document and compare. "
                   "Reply per claim with SUPPORTED or NOT SUPPORTED. If two high-reliability documents give different "
                   "answers for what the question asks about, or name different leaders, reply CONFLICT, even when the two documents use "
                   "different bases such as revenue and units. State both values and their bases. Never choose between them: a human decides.",
            tools=[mcp("fetch_document")],
            maxTurns=8,
        ),
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the six lines under **TODO 1** show `[PASS]`.

6. Review the definitions, noting the following details:

    - The `description` is what the coordinator reads to decide when to delegate to this specialist, so it says when to use it.
    - The analyst has two tools, `cagr` and `divide`. It can compute but it cannot search or read documents.
    - The fact-checker has one tool, `fetch_document`. It can re-read a source but it cannot search for a better one.
    - The fact-checker prompt says to report `CONFLICT` and never choose between two reliable sources. That is the escalation rule at the specialist level.
    - The `maxTurns` limit stops a specialist that loops.

## Block briefs that carry the confidential note

The coordinator knows the confidential note. Specialists must never see it, and a sentence in a prompt is not a guard. A PreToolUse hook runs in code before every delegation, and it can refuse the call.

1. In **lab.py**, search for the comment **TODO 2 of 3 - make_leak_guard**. Below it is the function `make_leak_guard(run)`, which contains an inner function named `guard`. Its only line is `return {}  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the eight-space indent, because the code sits inside two functions:

    ```python
            brief = json.dumps(input_data["tool_input"]).lower()
            if any(marker.lower() in brief for marker in LEAK_MARKERS):
                run.blocked_leaks += 1
                return {"hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "This brief contains client-confidential context. "
                                                "Rewrite it with only the research question and the facts needed.",
                }}
            return {}  # no opinion: allow
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the five lines under **TODO 2** show `[PASS]`.

5. Review the guard, noting the following details:

    - The hook reads the whole delegation, so the brief is checked wherever it appears in it, and the match ignores upper and lower case.
    - On a match, the hook counts the block and returns a `deny` decision. The reason goes back to the coordinator, so it can rewrite the brief without the note.
    - Returning `{}` means no opinion, and the call goes ahead.
    - The markers are specific phrases on purpose. A bare `$400M` would also block a legitimate brief about a Kestrel investor-day target, and the checker tests for that.

## Assemble the coordinator

The coordinator is one configuration object. It brings the specialists, the tools, the hook, and the limits together.

1. In **lab.py**, search for the comment **TODO 3 of 3 - build_options**. Below it is the function `build_options(run)`, and its only line is `return ClaudeAgentOptions(model=MODEL, system_prompt=COORDINATOR_PROMPT)  # replace these lines in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        server = create_sdk_mcp_server(SERVER, tools=[as_sdk_tool(spec) for spec in TOOL_SPECS])
        return ClaudeAgentOptions(
            model=MODEL,
            system_prompt=COORDINATOR_PROMPT,
            agents=SUBAGENTS,
            mcp_servers={SERVER: server},
            tools=["Agent"],                                                   # the coordinator's only built-in tool
            allowed_tools=[*DELEGATE_TOOLS, *(mcp(spec.name) for spec in TOOL_SPECS)],
            hooks={"PreToolUse": [HookMatcher(matcher="|".join(DELEGATE_TOOLS), hooks=[make_leak_guard(run)])]},
            max_turns=30,
            max_budget_usd=3.00,
            setting_sources=[],
        )
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 3** show `[PASS]`.

5. Review the configuration, noting the following details:

    - `agents=SUBAGENTS` gives the coordinator its four specialists.
    - `tools=["Agent"]` makes delegation the coordinator's only built-in tool, so it cannot search or calculate itself.
    - `allowed_tools` allows delegation and the five desk tools, because the subagents use them.
    - The `hooks` entry runs your leak guard before every delegation. The matcher names both `Agent` and `Task`, because the delegation tool was renamed between Claude Code versions.
    - The limits and `setting_sources=[]` work as they did in the Demo 3E agent: the desk is bounded, and every student's desk behaves the same.

## Run the desk on real questions

1. Run the desk on questions Q2 and Q5 by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit and takes a few minutes, because each question involves several specialists and several turns.

2. Watch the output, noting the following details:

    - Lines that start with `[coordinator] delegates to` show the coordinator handing work to a specialist.
    - Indented lines show the tool calls of that specialist.
    - Below each question, you see the final report and a list of `PASS` and `FAIL` checks from the scorer.
    - A final `info` line shows how many briefs the leak guard blocked, and how many data tools the coordinator called itself. The second number should be 0.

    > **Tip**: A model can occasionally take a different route. If the checker complains about the run, run `python lab.py` once more before you change any code.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 22/22 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Try breaking it (optional)

After you reach 22/22, change one thing at a time, run `python check.py`, and then undo the change.

1. Give the analyst the `fetch_document` tool as well. Which line fails, and what could the analyst now do that it should not?

2. Remove `.lower()` from the first line of the guard (`brief = json.dumps(...).lower()`), so that the match is case-sensitive. Which line fails, and why would a model that writes "DUE DILIGENCE" get through?

3. Remove the hook from `build_options`. Which lines fail? Part B would only fail if the coordinator actually tried to leak. What does that tell you about testing a control?

4. Add the confidential note to the system prompt of the writer. What would stop it from leaking?

## Troubleshooting

- **ANTHROPIC_API_KEY is missing**: The **.env** file is not in the lab folder, or it has a typo. Repeat the steps in *Set up the lab folder*.

- **The Claude Code CLI was not found**: The SDK could not find the command-line tool. Check that `claude --version` works in the same terminal.

- **IndentationError**: A pasted line lost its indent. The guard code is indented eight spaces, the `build_options` code is indented four spaces, and the two subagent entries are indented four spaces.

- **A TODO line still fails after pasting**: The old lines are still in the file, or you pasted only part of the snippet. Delete the old lines named in the step, and paste the whole snippet.

- **Part B says you edited lab.py after the last run**: Run `python lab.py` again.

- **A question shows FAIL in the scorer**: This is normal model variation. Run `python lab.py` once more before you change any code.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo.
