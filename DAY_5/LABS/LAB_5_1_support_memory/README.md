---
lab:
    title: 'Build the Memory Layer for a Hotel Reservations Agent'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Build the memory layer for a hotel reservations agent

Harbor Lane Hotels has a reservations agent that helps guests by chat. Dana from Northfield Consulting writes to it over five sessions: a first booking, a receipt, room needs, a team booking, and a stay extension. In session 1, Dana says: "never send me marketing email." In session 5, she asks the agent to email her the autumn offers. The API remembers nothing between calls, so a correct agent must find that rule again. In this lab, you build the memory layer that makes it possible.

You will complete four small pieces of **lab.py**, which add up to 15 lines of code. The lab takes about 40 minutes, and this guide gives you every line. Claude extracts the facts, your code saves them, loads only the ones a request needs, and compacts the old history while keeping the rule pinned.

This lab continues Demo 5A, so you will recognize the following:

- One guest, five sessions, and one hard rule that appears in session 1 and matters in session 5.
- The start state: the whole history in the prompt, with the input tokens growing on every call.
- The load, work, save loop: a fast model extracts durable facts into **results/memory.json**, and a new process loads only what it needs.
- Compaction with a pinned rule: the old history becomes a summary, and the hard rule stays above it in its exact words.
- The retention check: code that proves the rule survived.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_5/LABS/LAB_5_1_support_memory** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Create a new file named **.env** in the lab folder, and add the following line, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

4. Save the file, and then test your key by running the following command:

    ```
    python claude_client.py
    ```

5. Verify that you see a short greeting followed by a line that starts with `[usage]`.

## Review the starting point

1. Run the checker by running the following command:

    ```
    python check.py
    ```

    This command tests your code with hand-made inputs. It needs no key and no model, so it is the quickest way to see whether a TODO works.

    > **Note**: The checker reports `[FAIL]` lines because your TODOs are not written yet. Part B is skipped until you run the four lab commands.

2. Notice that three files matter for this lab: **lab.py**, which holds your four TODOs, **check.py**, and **data/sessions.json**, which holds Dana's five sessions. The **memory_core.py** file holds the helpers from the demo, and you do not need to read it.

3. Open **lab.py**, and find the function `ask_claude`. It is the one Claude API call in this lab. It sends one prompt with `client.messages.create(...)`, and it returns the answer text and the number of input tokens that the API reported. You do not edit it.

## Run the start state

Before you build the memory layer, see the problem it solves. The history lives only in the prompt.

1. Answer all five sessions with every earlier session in the prompt by running the following command:

    ```
    python lab.py history
    ```

    This command calls Claude once per session, and then asks one more question with no history at all. You run it first so that you see the problem before the fix.

    > **Note**: The run makes seven short calls to Claude, and uses a small amount of API credit.

2. Verify that the table shows the input tokens rising on every row, for example from about 250 on session 1 to about 700 on session 5, and that the answer to the last question says the agent has no record of Dana's email wishes.

    > **Tip**: The model did not forget. It never saw session 1. The history lived only in the prompt, and the API remembers nothing.

## Save facts

After each session, a fast model extracts the durable facts. You write the code that wraps each fact in a record and saves it. A record carries its source session and the time it was saved, so you can always see where a fact came from.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 4 - SAVE FACTS**. Below it are two functions, `make_record` and `extract_facts`. Each one has a single placeholder line that ends with `# replace these lines in TODO 1`.

3. In the `make_record` function, replace the line `return {}  # replace these lines in TODO 1` with the following code. Keep the four-space indent:

    ```python
        hard_rule = bool(item.get("hard_rule"))
        return {"fact": item["fact"], "tags": item["tags"], "hard_rule": hard_rule,
                "source_session": session["id"], "saved_at": session["date"], "scope": core.SCOPE,
                "version": 1, "ttl_days": None if hard_rule else core.DEFAULT_TTL_DAYS}
    ```

4. In the `extract_facts` function, replace the line `return []  # replace these lines in TODO 1` with the following code:

    ```python
        reply, _ = ask_claude(MODEL_FAST, core.EXTRACT_SYSTEM, core.transcript([session]))
        return [make_record(item, session) for item in core.parse_json_list(reply)]
    ```

5. Save the file, and then run `python check.py`.

6. Verify that the five lines under **TODO 1** show `[PASS]`.

7. Review the code, noting the following details:

    - `source_session` and `saved_at` say where a fact came from and when it was saved.
    - `scope` says whose fact it is, so one guest's facts never reach another guest.
    - `ttl_days` is the time to live. A normal fact lasts 90 days, and a hard rule has `None`, so it never expires.
    - `extract_facts` uses `MODEL_FAST`, the cheap model, because extraction is a simple job. The main model answers the guest.
    - The prompt in `core.EXTRACT_SYSTEM` asks the model for a JSON list, and `core.parse_json_list` finds that list in the reply.

8. Extract and save the facts of sessions 1 to 4 by running the following command:

    ```
    python lab.py save
    ```

    This command calls the fast model once per session, runs your two functions, and writes the records to **results/memory.json**. You run it now because the next two parts read that file.

9. Verify that the output lists about nine saved facts, each with its tags and the session it came from, and that the no-marketing rule shows `none` under `ttl`.

## Load facts

A new process starts with an empty prompt. It reads **results/memory.json** and loads only the facts that the request needs. Hard rules always come along, so a keyword miss can never hide them.

1. In **lab.py**, search for the comment **TODO 2 of 4 - LOAD FACTS**. Below it is the function `select_facts(question, memory, today)`, and its only line is `return []  # replace these lines in TODO 2`.

2. Replace that line with the following code. Keep the four-space indent:

    ```python
        wanted = core.tags_for(question)
        return [r for r in memory
                if r["scope"] == core.SCOPE and core.is_current(r, today) and (r["hard_rule"] or wanted & set(r["tags"]))]
    ```

3. Save the file, and then run `python check.py`.

4. Verify that the five lines under **TODO 2** show `[PASS]`.

5. Review the code, noting the following details:

    - `core.tags_for(question)` finds the topics of the request by simple keyword match. Session 5 mentions nights in Porto and email offers, so the topics are `booking` and `contact`.
    - A fact is loaded only when it belongs to this guest, has not run out of time, and is either a hard rule or shares a topic with the request.
    - Billing facts, room facts, and the late check-in fact are left out, because this request does not need them.

6. Start a new process that loads, works, and saves, by running the following command:

    ```
    python lab.py load
    ```

    This command reads only **results/memory.json**. It loads the facts that match the request, answers with the main model, and saves any new fact back to the file. It is a separate command from the save, so it is a real new process, and the rule can only come from the file.

7. Verify that the output loads a few facts out of the total, for example 3 of 9, that the no-marketing rule is among them, and that the agent confirms the stay but does not promise marketing email. The input token count is far smaller than the 700 or so tokens of the history run.

## Pin the hard rule

When a history gets too long, you compact it into a summary. A summary is lossy, and it can drop the one sentence that mattered. So the hard rule is copied above the summary in its exact words. The summary prompt never mentions it.

1. In **lab.py**, search for the comment **TODO 3 of 4 - COMPACT**. Below it are two functions, `pinned_rules` and `compact_context`.

2. In the `pinned_rules` function, replace the line `return []  # replace this line in TODO 3` with the following code. Keep the four-space indent:

    ```python
        return [record["fact"] for record in memory if record["hard_rule"]]
    ```

3. In the `compact_context` function, replace the line `return summary  # replace these lines in TODO 3` with the following code:

    ```python
        rules = "\n".join(f"- {rule}" for rule in pinned)
        pinned_part = f"Hard rules (exact words, never summarised):\n{rules}"
        return f"{pinned_part}\n\nSummary of earlier sessions:\n{summary}"
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the three lines under **TODO 3** show `[PASS]`.

    > **Note**: The pinned list comes from memory, not from the summary. Even if the summary leaves out the rule, the context still holds it, word for word.

## Check that the rule survived

A claim that the rule survived is only worth something if code can check it. These two small functions are plain string checks. They need no model, and they give the same answer every time.

1. In **lab.py**, search for the comment **TODO 4 of 4 - THE RETENTION CHECK**. Below it are two functions, `rules_survive` and `memory_has_rule`.

2. In the `rules_survive` function, replace the line `return True  # replace this line in TODO 4` with the following code. Keep the four-space indent:

    ```python
        return all(rule in context for rule in pinned)
    ```

3. In the `memory_has_rule` function, replace the line `return False  # replace this line in TODO 4` with the following code:

    ```python
        return any(r["hard_rule"] and "marketing" in r["fact"].lower() for r in memory)
    ```

4. Save the file, and then run `python check.py`.

5. Verify that the three lines under **TODO 4** show `[PASS]`.

6. Summarise sessions 1 to 4, pin the rule, and check that it survived, by running the following command:

    ```
    python lab.py compact
    ```

    This command asks the fast model for a short summary of sessions 1 to 4, and then runs your functions to pin the rule and to check it. It finally answers Dana's request from the compacted context, so you see that the agent still follows the rule.

7. Verify that the compacted context is smaller than the history, for example about 150 tokens against about 500, that both rule lines say `yes`, and that the agent does not promise marketing email.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

    This command runs Part A on your functions, and Part B on the results that the four lab commands saved. It is the only evidence this lab needs.

2. Verify that the last line reads:

    ```
    RESULT: 25/25 checks passed
    ```

3. Submit the **results/run.json** file as your evidence. There is nothing else to write up.

    > **Note**: The lines that start with `[info]` show whether each reply promised marketing email. They are for you to read, and they do not change the result.

## Clean up

Delete the **results** folder to reset the lab, and keep your **.env** file private.

## More information

The **SOLUTION/lab_solution.py** file is the finished lab. This guide already contains every line you need, so use the file only to compare your work. To learn how the API call works, see **HOW_THE_CODE_WORKS.md** in the **STUDENT_V2** folder. The study guide for this topic is **STUDENT_V2/STUDY_GUIDES/DAY_5/CONTEXT_AND_MEMORY.md**.
