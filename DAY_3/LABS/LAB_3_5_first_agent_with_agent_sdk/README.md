---
lab:
    title: 'Build Your First Agent with the Claude Agent SDK'
    module: 'Day 3 - Agentic Architecture and Orchestration'
---

# Build Your First Agent with the Claude Agent SDK

In Demo 3E, you watched a security-analyst agent triage incident INC-7741 at Nordlicht Logistics. The agent was given one goal and no steps. It listed the alerts, read the logs of the suspicious host, looked up the suspicious IP addresses, and wrote a verdict. The whole agent was one configuration object: a model, a system prompt, a set of tools, and limits. In this lab, you build that agent yourself, with the same incident, the same threat feed, and the same three read-only tools.

You will complete four small pieces of **lab.py**, which add up to 32 lines of code. The lab takes about 30 minutes, and this guide gives you every line. At the end, your agent triages the incident for real.

This lab continues Demo 3E, so you will recognize the following:

- The incident INC-7741 and its alerts, log lines, and threat-intelligence feed.
- The three read-only tools: `list_alerts`, `get_log_lines`, and `lookup_indicator`.
- The five ideas from the demo: the agent loop that you never write, tool descriptions that guide tool choice, least privilege, bounded autonomy, and a human who stays in charge.

## Set up the lab folder

> **Note**: This lab needs two things from **DAY_0_SETUP_GUIDE.md**: the `claude-agent-sdk` package (section 3) and the Claude Code command-line tool (section 8). If either is missing, finish that part of the Day 0 guide first.

You need Python 3.10 or later, an Anthropic API key, and the Claude Code command-line tool, because the Agent SDK runs it as a helper process.

1. Open a terminal in the **STUDENT_V2/DAY_3/LABS/LAB_3_5_first_agent_with_agent_sdk** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Verify that the Claude Code command-line tool is installed by running the following command:

    ```
    claude --version
    ```

    > **Note**: The SDK uses your API key. Do not sign in with a claude.ai account.

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

    > **Note**: Part A tests your four TODOs with no API key and no model. Part B is skipped until you run the agent. The lines under each TODO turn to `[PASS]` as you complete it.

2. Notice that only two files matter for this lab: **lab.py**, which holds your four TODOs, and **check.py**. The **soc_tools.py** file holds the three tool functions, which read the incident data, and you do not need to read it.

## Describe the tools to Claude

A tool is a function plus a description. Claude reads the description to decide when to call the tool, so write it like a hand-over note: what the tool returns, and when to use it.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - TOOL_SPECS**. Below it is a list of three rows, each with a name, a one-word description, and an empty schema.

3. Select the three rows inside the `TOOL_SPECS = [` list, and replace them with the following code:

    ```python
        {"name": "list_alerts",
         "description": "List the security alerts for the incident. Optionally pass a host name to see only that host.",
         "schema": {"type": "object", "properties": {"host": {"type": "string"}}}},
        {"name": "get_log_lines",
         "description": "Return the raw log lines for one host, oldest first. Use it to confirm what an alert claims.",
         "schema": {"host": str}},
        {"name": "lookup_indicator",
         "description": "Look up an IP address in the threat-intelligence feed. Returns reputation and campaign.",
         "schema": {"ip": str}},
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the five lines under **TODO 1** show `[PASS]`.

6. Review the descriptions, noting the following details:

    - `list_alerts` says what it returns and that the host is optional.
    - `get_log_lines` says what it returns and when to use it: to confirm what an alert claims. That sentence teaches the agent to check alerts against the logs.
    - `lookup_indicator` says what it looks up and what comes back.
    - The schema tells Claude what input each tool takes: an optional host, a required host, and a required IP address.

## Write the system prompt

The system prompt says who the agent is and what a good answer looks like. It does not list the steps, because choosing the steps is the agent's job.

1. In **lab.py**, search for the comment **TODO 2 of 4 - SYSTEM_PROMPT**. Below it is the line `SYSTEM_PROMPT = "You are a helpful assistant."`.

2. Replace that line with the following code:

    ```python
    SYSTEM_PROMPT = """You are a security analyst triaging one incident.
    Investigate with your tools; do not guess. Ignore alerts that the logs do not support.
    Finish with a short report:
      1. Verdict: confirmed compromise, suspected, or false alarm.
      2. Evidence: three bullets, each citing a log line or intel result.
      3. Next action: one recommended step, for a human to approve. You cannot act yourself."""
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the two lines under **TODO 2** show `[PASS]`.

    > **Note**: The prompt describes the outcome, not the route. "You cannot act yourself" keeps the human in charge, and "do not guess" tells the agent to use its tools.

## Configure the agent

An agent in the SDK is one configuration object. This is where you decide what the agent may do and when it must stop.

1. In **lab.py**, search for the comment **TODO 3 of 4 - build_options**. Below it is the function `build_options()`, and its only line is `return ClaudeAgentOptions(model=MODEL)  # replace these lines in TODO 3`.

2. Replace that line with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        server = create_sdk_mcp_server("soc", tools=[as_sdk_tool(spec) for spec in TOOL_SPECS])
        return ClaudeAgentOptions(
            model=MODEL,
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"soc": server},
            tools=[],                                   # switch OFF Claude Code's built-in file and shell tools
            allowed_tools=["mcp__soc__list_alerts",     # pre-approve exactly these three, nothing else
                           "mcp__soc__get_log_lines",
                           "mcp__soc__lookup_indicator"],
            max_turns=12,                               # limit on the loop
            max_budget_usd=1.00,                        # limit on spend
            setting_sources=[],                         # ignore any local CLAUDE.md or settings files
        )
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the six lines under **TODO 3** show `[PASS]`.

5. Review the configuration, noting the following details:

    - `create_sdk_mcp_server` bundles your tools into a server that runs inside your own Python process. There is nothing separate to start.
    - `tools=[]` switches off Claude Code's built-in file and shell tools. This is least privilege: the agent can only read the incident.
    - `allowed_tools` pre-approves exactly three tools. A tool name has the form `mcp__<server>__<tool>`.
    - `max_turns` and `max_budget_usd` set the limits. They are bounded autonomy: the agent chooses its steps within limits you configure.
    - `setting_sources=[]` ignores any local settings files, so every student's agent behaves the same.

## Run the agent loop

The `query()` function runs the whole loop for you: it asks Claude, runs the tools Claude requests, sends the results back, and repeats until Claude is done. It streams messages, and the helper functions in the file turn each message into a simple event to print.

1. In **lab.py**, search for the comment **TODO 4 of 4 - run_live**. Below it is the function `run_live()`, which contains the line `pass  # replace this line in TODO 4`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        async for message in query(prompt=GOAL, options=build_options()):
            for event in events_from(message):
                show(event)
                all_events.append(event)
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the one line under **TODO 4** shows `[PASS]`.

    > **Note**: You never write the loop. `query()` is the loop, and your code only reads what comes out of it.

## Run your agent on the incident

1. Run your agent by running the following command:

    ```
    python lab.py
    ```

    > **Note**: The run uses a small amount of API credit. The agent chooses its own tool calls, so the order differs from run to run.

2. Watch the output. You should see lines that start with `-> tool:` as the agent calls its tools, then a short report, and then a line that starts with `[done]`. For example:

    ```
      -> tool: list_alerts({})
      -> tool: get_log_lines({"host": "bastion-02"})
      -> tool: lookup_indicator({"ip": "203.0.113.50"})

    Verdict: confirmed compromise on bastion-02. ...

    [done] ok | turns=5 | cost=$0.0200 | stop_reason=end_turn
    ```

    > **Note**: The agent might take a different route from the example. That is normal.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 18/18 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to find a typo.
