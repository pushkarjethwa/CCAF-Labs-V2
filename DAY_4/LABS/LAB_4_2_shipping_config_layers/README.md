---
lab:
    title: 'Layer the CLAUDE.md, Rules and Hooks of a Shipping Repo'
    module: 'Day 4 - Claude Code Configuration and Workflows'
---

# Layer the CLAUDE.md, rules and hooks of a shipping repo

In Demo 4B, you built the instruction layers of the notification-service repo one stage at a time, and you saw that instruction files are concatenated, not ranked. A tenant's report said 3.12 while its invoice said 3.13, because the report used `float`. You fixed it by writing the layers so that nothing contradicts, and then you enforced the money rule with a hook. In this lab, you apply the same method to a different repo: `shipcalc`, the library that prices parcels for two carriers. Its quote is an integer number of cents, yet one function still computes the price with `float`, so a half-cent tie rounds the wrong way.

You will fill in five small pieces across five stages, which add up to 25 lines, and this guide gives you every line. At each stage you ask Claude Code which files it loaded, and you run a key-free checker that measures the result. The lab takes about 30 minutes.

This lab continues Demo 4B, so you will recognize the following:

- The layers, added in the same order: the user file, the project `CLAUDE.md`, a subdirectory `CLAUDE.md`, and path-scoped rules in **.claude/rules/** with an `@` import.
- The questions you ask at each stage: which instruction files are in your context, and which file did each rule come from.
- The one rule that must never break, moved out of prose and into a PostToolUse hook and a scanner.
- The idea behind all of it: files are concatenated, so you write each fact once, and you enforce what matters in code.

The repo is new, and so is one extra layer: a project **.mcp.json** file at the end.

## Set up the lab folder

> **Note**: This lab needs Claude Code to be installed and signed in, as set up in **DAY_0_SETUP_GUIDE.md** (section 8). You can run the checker without Claude Code or an API key.

You need Python 3.10 or later and the Claude Code command-line tool.

1. Open two terminals. Both start in the **STUDENT_V2/DAY_4/LABS/LAB_4_2_shipping_config_layers** folder. The first terminal stays there, and you use it for the checker and **reset.py**. In the second terminal, go to the **STARTER/repo** folder, and later run Claude Code there.

2. Install pytest by running the following command:

    ```
    pip install -r requirements.txt
    ```

3. Verify that the Claude Code command-line tool is installed by running the following command:

    ```
    claude --version
    ```

## Review the starting point

1. Run the checker by running the following command:

    ```
    python check.py
    ```

    > **Note**: The checker tests your work with no API key and no model. Each line shows `[PASS]` when a piece is done, and `[todo]` while it is not. At the start, almost every line shows `[todo]`.

2. Notice that you work in the **STARTER** folder. The **STARTER/repo** folder is the shipcalc repo. It has working code and passing tests, but its five instruction files hold only a placeholder line. The **STARTER/home_claude/CLAUDE.md** file is the user-level file, and you install it later with **reset.py**.

3. In the second terminal, start Claude Code:

    ```
    claude
    ```

4. Type this prompt:

    ```
    List every instruction file you have loaded for this project, and every rule you are following about money and about tests. If there are none, say so.
    ```

    > **Note**: Claude says that it has no project instructions. Nothing in this repo tells it whether a price is an integer or a float.

5. Type `/exit`. You will repeat the same pattern at every stage: fill in the files, run `python check.py`, and then start a new `claude` session, because instruction files are read when a session starts.

## Add the user and project layers

The user file lives in your home folder and follows you into every project. The project file lives in the repo and is shared through git. Claude loads both when the session starts.

1. Open **STARTER/home_claude/CLAUDE.md** in your code editor, and replace its content with the following line:

    ```markdown
    - Keep answers concise; show the command you ran.
    ```

2. Open **STARTER/repo/CLAUDE.md**, and replace its content with the following lines:

    ```markdown
    # shipcalc
    Tests: `python -m pytest`. Money rule check: `python .claude/hooks/invariants.py src`.
    - Internal units are kilograms and centimetres.
    - Money is integer cents everywhere.
    - Diagnostics go through `logging`, never `print()`.
    ```

3. In the first terminal, install the user file by running the following command:

    ```
    python reset.py --user install
    ```

4. Run `python check.py`, and verify that the two lines under **Stage 1** show `[PASS]`.

5. In the second terminal, start `claude`, type `/memory`, and then type this prompt:

    ```
    Which instruction files are loaded? For each file, quote what it says about money, print and tests. Then run the tests and show me the command you ran.
    ```

6. Verify that `/memory` lists **~/.claude/CLAUDE.md** and the project **CLAUDE.md**, that Claude quotes "integer cents" and "never `print()`", and that the tests pass.

    > **Important**: Keep the user file to personal style only. A number-type preference there would contradict the project file, and nobody would see the conflict in a code review.

7. Review the two files, noting the following details:

    - The user file holds one personal preference, and it shows in the style of Claude's answer: concise, with the command shown.
    - The project file is five lines, and each fact appears once.
    - Units and money are stated in the project file because they apply everywhere. Later layers add detail, and they never restate or reverse a fact.

8. Type `/exit`.

## Add the subdirectory layer

A **CLAUDE.md** file inside a subdirectory is lazy. It is not loaded at launch. It arrives when Claude reads a file in that folder.

1. Open **STARTER/repo/src/shipcalc/carriers/CLAUDE.md**, and replace its content with the following lines:

    ```markdown
    # carriers/
    - Every adapter starts with `units.to_metric(parcel)`; after that, everything is kg and cm.
    - A new carrier is one module here plus a divisor in `rates.DIVISORS`.
    ```

2. Run `python check.py`, and verify that the two lines under **Stage 2** show `[PASS]`.

3. In the second terminal, start `claude` again, and type this prompt:

    ```
    Read src/shipcalc/rates.py. Then list the instruction files that are in your context right now.
    ```

4. Type this second prompt:

    ```
    Now read src/shipcalc/carriers/acme.py and list the instruction files in your context again. What is new?
    ```

5. Verify that after the first prompt Claude lists the user file and the project file, and that after the second prompt **src/shipcalc/carriers/CLAUDE.md** is new.

    > **Note**: Whether `/memory` also lists the nested file at this point depends on your version of Claude Code, so verify on your Claude Code version.

6. Review the file, noting the following details:

    - It describes only the carriers folder, and it says nothing about money or style, so it cannot contradict another layer.
    - The same repo gives Claude a different context depending on which file it is reading. This is why "it worked when I tried it" is a poor test of instruction design.

7. Type `/exit`.

## Add the path-scoped rules and the import

Rules live in **.claude/rules/**, one topic per file. The only front matter key a rule reads is `paths:`. A rule loads when Claude reads a file that matches one of its globs.

1. Open **STARTER/repo/.claude/rules/money.md**, and replace its content with the following lines:

    ```markdown
    ---
    paths:
      - "src/shipcalc/**/*.py"
    ---
    - Never use float, round() or a float literal for a price; apply zone multipliers as integer permille.
    - Round half-up once, at the end: (cents * permille + 500) // 1000.
    ```

2. Open **STARTER/repo/.claude/rules/tests.md**, and replace its content with the following lines:

    ```markdown
    ---
    paths:
      - "tests/**/*.py"
    ---
    - Add a regression test for every money bug; half-cent tie cases are mandatory.
    ```

3. Add the architecture document to the project file. Open **STARTER/repo/CLAUDE.md**, and add the following line at the end:

    ```markdown
    Architecture: @docs/ARCHITECTURE.md
    ```

4. Run `python check.py`, and verify that the first four lines under **Stage 3** show `[PASS]`. The last three lines pass after Claude updates the code in the next steps.

5. In the second terminal, start `claude` again, and type this prompt:

    ```
    Read src/shipcalc/rates.py. List the instruction files in your context, and say which file each money rule came from.
    ```

6. Type this second prompt:

    ```
    Update rates.py so that it follows the rules that apply to it. Add a regression test named test_half_cent_tie_rounds_up for a 3 kg parcel in zone 2, which must cost 863 cents. Then run the tests.
    ```

7. Type this third prompt:

    ```
    Read tests/test_quote.py. Which rule file is in your context for it, and what does it ask for?
    ```

8. Verify the following results:

    - After the first prompt, Claude names **money.md** as the source of the money rules, and **CLAUDE.md** as the source of "integer cents".
    - After the second prompt, Claude replaces the float arithmetic in `price_cents` with integer arithmetic, adds the tie test, and the tests pass.
    - After the third prompt, Claude names **tests.md** and says that it asks for a regression test with half-cent ties.
    - In the first terminal, `python check.py` shows all of **Stage 3** as `[PASS]`.

    > **Note**: Claude's exact code differs from run to run. What matters is that the price is an integer and that the tie case costs 863 cents. A 3 kg parcel in zone 2 is 750 cents times 1.15, which is 862.5, and float arithmetic rounds it down to 862.

9. Review the layers, noting the following details:

    - Each rule file has one topic and one `paths:` list. The money rule applies to all source files, and the tests rule applies to the tests.
    - No file says "float" in a way that conflicts with another. Every fact lives in one place, and the layers add detail without reversing each other.
    - The `@docs/ARCHITECTURE.md` import organizes the file, but it expands at launch, so it does not save tokens.
    - After a `/compact`, nested files and path rules can disappear until Claude reads a matching file again. A rule that must survive a long session belongs in the root file, or better, in a hook.

10. Type `/exit`.

## Enforce the rule with a hook

A consistent instruction is still only text. The scanner **.claude/hooks/invariants.py** and the hook script **.claude/hooks/enforce_money.py** are already in the repo. You wire the hook script into Claude Code.

1. Create a new file named **STARTER/repo/.claude/settings.json**, and add the following lines:

    ```json
    {"hooks": {"PostToolUse": [{"matcher": "Edit|Write|MultiEdit",
      "hooks": [{"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/enforce_money.py\"", "timeout": 20}]}]}}
    ```

2. Run `python check.py`, and verify that the three lines under **Stage 4** show `[PASS]`.

3. In the second terminal, start `claude` again, and type `/hooks`.

4. Verify that `/hooks` lists a PostToolUse hook for `Edit|Write|MultiEdit`.

5. Type this prompt:

    ```
    Add a function quote_all(parcel, zone) to src/shipcalc/quote.py that returns a dict of carrier name to price in cents for every carrier. Add a test for it, and run the tests.
    ```

6. Verify that Claude adds the function with integer cents, that the hook does not complain, and that the tests pass.

7. Type `/exit`. In the second terminal, which is still in **STARTER/repo**, run the scanner and the tests:

    ```
    python .claude\hooks\invariants.py src
    python -m pytest -q
    ```

8. Verify that the scanner prints `MONEY INVARIANT: ok` and that the tests pass.

9. Review the hook, noting the following details:

    - The hook runs after every Edit, Write or MultiEdit. It re-scans Python files under **src/shipcalc**, whatever Claude read earlier.
    - The hook exits with code 0 when the code is clean. With exit code 2, it would send its message back to Claude to fix. Exit code 1 would not.
    - On Windows, the file path arrives with backslashes, and the script normalizes them.
    - The rule now exists twice, on purpose: the sentence guides Claude, and the hook enforces it.

## Declare the project MCP server

The last layer is the project **.mcp.json** file. Like the project `CLAUDE.md`, it lives in the repo and is shared through git, so it must never hold a credential.

1. Create a new file named **STARTER/repo/.mcp.json**, and add the following lines:

    ```json
    {"mcpServers": {"carrier-docs": {"type": "http", "url": "https://docs.example.com/mcp",
      "headers": {"Authorization": "Bearer ${CARRIER_DOCS_TOKEN}"}}}}
    ```

2. Run `python check.py`, and verify that the two lines under **Stage 5** show `[PASS]`.

3. In the second terminal, start `claude` again, approve the project MCP server when Claude Code asks, and type `/mcp`.

4. Verify that `/mcp` lists **carrier-docs**.

    > **Note**: The URL is a placeholder for your team's carrier-documentation server, and this lab checks only the declaration. Set the `CARRIER_DOCS_TOKEN` environment variable when you have a real server.

5. Review the file, noting the following details:

    - The `${CARRIER_DOCS_TOKEN}` value is read from your environment, so the secret stays out of git.
    - Claude Code asks for approval before it uses a server that a project file declares.

## Check your work

1. Run the checker one last time:

    ```
    python check.py
    ```

2. Verify that the last line reads:

    ```
    RESULT: 16/16 checks passed
    ```

3. Submit the output of `python check.py` as your evidence. There is nothing else to write up.

## Clean up

1. Remove the user-level file by running the following command. Your own file is restored if you had one:

    ```
    python reset.py --user remove
    ```

## More information

The **SOLUTION** folder is the finished lab, laid out like **STARTER**. This guide already contains every line you need, so use the folder only to find a typo. To check it, run `python check.py --root SOLUTION`.

The layers you built follow one design: files are concatenated and not ranked, a nested file and a path rule load only when Claude reads a matching file, and a critical rule is enforced by a hook or a test. Deterministic precedence exists only in settings and permissions.
