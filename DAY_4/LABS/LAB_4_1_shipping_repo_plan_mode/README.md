---
lab:
    title: 'Explore, Plan and Refactor a Repository with Claude Code'
    module: 'Day 4 - Claude Code in the Development Workflow'
---

# Explore, plan and refactor a repository with Claude Code

In Demo 4A, you saw one broad sentence, "consolidate all rounding into one module and update every caller", turn into a safe change. You explored the repository first, decided with a rubric whether to plan, planned in Plan Mode, and implemented the plan one step at a time while the tests ran after every edit. In this lab, you repeat that method on a different repository: **shipcalc**, a small shipping-quote library at a parcel company. Customers enter pounds and inches, or kilograms and centimetres, and two carrier adapters, `acme` and `zipfast`, price the parcel.

The tests are green, yet imperial parcels are mis-priced, and the cause is spread over several modules. You work in Claude Code on the sample repository, and you paste in about 25 lines: two small configuration files, a few lines of CLAUDE.md, and eleven prompts. The lab takes about 35 minutes, and at the end a key-free checker confirms your work.

This lab continues Demo 4A, so you will recognize the following:

- The four stages: explore, decide direct or plan, plan in Plan Mode, and implement and verify.
- The **CLAUDE.md** file, the **/triage** slash command, the **/plan-check** slash command and its plan gate, and the `PostToolUse` hook that runs the tests after every edit.
- The acceptance script that lives outside **tests/**, and the unrelated finding that gets its own change.

## Set up the lab folder

You need Python 3.10 or later and the Claude Code command-line tool, signed in. The lab uses only the Python standard library.

1. Open a terminal in the **STUDENT_V2/DAY_4/LABS/LAB_4_1_shipping_repo_plan_mode** folder.

2. Verify that Claude Code is installed by running the following command:

    ```
    claude --version
    ```

3. Move into the repository, and run its tests by running the following commands:

    ```
    cd STARTER
    python -m unittest discover -s tests
    ```

4. Verify that the output ends with `Ran 10 tests` and `OK`.

5. Run the acceptance script by running the following command:

    ```
    python scripts/hidden_regression_units.py
    ```

    > **Note**: The script reports `FAILED (failures=4)`. It is not part of the test suite, and it is your target: when you finish, its four checks pass.

6. Open a second terminal in the **STARTER** folder. Use the first one for Claude Code, and the second one to run commands yourself.

## Explore the repository

Nothing in this stage edits a file. Claude reads and searches, so you pay for knowledge, not for edits.

1. Open **CLAUDE.md** in your code editor, and find the line that starts with `TODO(student)`.

2. Replace that line with the following two lines:

    ```
    - Read before you edit: search for every definition and every caller first.
    - Keep unrelated findings out of the change; report them separately.
    ```

3. Save the file, and then start Claude Code in the first terminal:

    ```
    claude
    ```

4. Type the following prompt:

    ```
    Before changing anything: find every place that reads a parcel's weight or dimensions, every caller, and every test that exercises them. Do not edit files.
    ```

5. When Claude finishes, type the following prompt:

    ```
    Which tests would notice if the zipfast adapter used pounds as kilograms? Check the tests and scripts folders. Also name any unrelated defect you notice in rates.py.
    ```

6. In the second terminal, cross-check Claude's answer by running the following command:

    ```
    python tools/blast_radius.py
    ```

7. Review the results, noting the following details:

    - Claude lists `acme.py` and `zipfast.py` as the modules that read the parcel, and `packaging.py` as the module they call. Nobody asked about `packaging.py`.
    - Claude says that no test in **tests/** would notice the pound mistake, because the only imperial test uses a 2x2x2 inch parcel with almost no volume. The script in **scripts/** would notice.
    - Claude's wording differs on every run. The `blast_radius.py` output is the fixed reference.
    - Claude may report that an unknown zone number raises a bare `KeyError`. Keep that finding for stage 4.

    > **Note**: **CLAUDE.md** is read automatically at the start of each session. The **.claude/settings.json** file lets Claude run the tests, the acceptance script and the two tools without asking.

## Decide: direct or plan?

A rubric turns "should I plan?" into a repeatable answer. You write it once, as a slash command, and use it on every request.

1. Type `/exit` to leave Claude Code.

2. Create a new file named **triage.md** in the **.claude/commands** folder, and add the following content:

    ```
    ---
    description: Decide DIRECT or PLAN for a change request
    ---

    Triage this change request: $ARGUMENTS

    Do not edit any file. Look at the repo with read-only tools, then answer `DIRECT` or `PLAN`, followed by the signals that fired.
    Plan first if ANY of these is true: the change touches 4 or more files, a shared symbol has 3 or more callers, it involves money, it is hard to reverse, test coverage is weak, or the scope is unknown. Otherwise it is DIRECT.
    ```

3. Start Claude Code again by running `claude`, and then type the following prompt:

    ```
    /triage Change the unknown-carrier error message to start with a capital letter
    ```

4. Type the following prompt:

    ```
    /triage Imperial parcels are mis-priced. Make every carrier convert weight and dimensions correctly, in one place
    ```

5. Type the following prompt, and approve the edits and the test run when Claude asks:

    ```
    Change the unknown-carrier error to "Unknown carrier: <name>" and add a test for the message in tests/test_errors.py. Run the tests and show me the diff.
    ```

6. Verify that the test run ends with `Ran 11 tests` and `OK`.

7. Review the results, noting the following details:

    - The wording change is `DIRECT`: it touches two files, and no signal fires.
    - The unit-handling request is `PLAN`. Claude names the signals: a shared conversion with several callers, money, and weak coverage.
    - The direct change edits **quote.py** and adds **tests/test_errors.py**. Read the approval prompt before you approve the first edit.

## Plan the change in Plan Mode

Plan Mode is a permission mode, not a smarter model. Claude reads, searches and writes a plan, and it cannot edit your source until you approve.

1. Type `/exit`, and then restart Claude Code in Plan Mode:

    ```
    claude --permission-mode plan
    ```

2. Type the following prompt:

    ```
    Imperial parcels are mis-priced. Make every carrier convert weight and dimensions correctly, in one place, and update every caller. Use what you found. Include files, callers, risks, order, verification and rollback. Put any unrelated defect in its own separate final step.
    ```

3. Read the plan like a pull request. Choose to keep planning, and then type the following prompt:

    ```
    Check that your plan puts a characterization test first, covers dimensional weight in both adapters, and runs scripts/hidden_regression_units.py. Revise it if not.
    ```

4. Approve the revised plan, and then type the following prompt:

    ```
    Save the approved plan to docs/PLAN.md. Do not change any other file.
    ```

5. Type the following prompt:

    ```
    /plan-check docs/PLAN.md
    ```

6. Verify that the last line of the output reads `PLAN ACCEPTED (15/15 checks)`.

7. Review the plan, noting the following details:

    - A good plan names `acme.py`, `zipfast.py`, `packaging.py` and `units.py`, and says how each step is verified.
    - The zipfast adapter has a pound mistake, and the acme adapter has a different one: it passes inches into the centimetre formula for dimensional weight. A one-line fix to zipfast leaves acme wrong.
    - The unknown-zone defect sits in its own final step, not mixed into the refactor.
    - Your wording differs from the reference plan in **SOLUTION/docs/PLAN.md**.

    > **Note**: The status line shows that Plan Mode is on. In a normal session, press Shift+Tab to cycle to it.

## Implement and verify

The plan is a contract. Claude runs the tests after every step, and a hook runs them again after every edit it makes, so you never rely on "it says it is done".

1. Type `/exit`.

2. Replace the contents of **.claude/settings.json** with the following code:

    ```
    {
      "permissions": {"allow": ["Bash(python -m unittest:*)", "Bash(python scripts/hidden_regression_units.py)", "Bash(python tools/blast_radius.py:*)", "Bash(python tools/plan_check.py:*)"]},
      "hooks": {"PostToolUse": [{"matcher": "Edit|Write", "hooks": [{"type": "command", "command": "python -m unittest discover -s tests"}]}]}
    }
    ```

3. Start Claude Code in the normal mode by running `claude`, and then type the following prompt:

    ```
    Implement docs/PLAN.md one step at a time, except the separate final step. Put the characterization test in tests/test_characterization.py and the regression tests in tests/test_imperial_regression.py. After each step run python -m unittest discover -s tests and python scripts/hidden_regression_units.py, and tell me both results.
    ```

4. Watch the results after each step. When Claude finishes, run `python scripts/hidden_regression_units.py` in the second terminal.

5. Verify that the script ends with `Ran 4 tests` and `OK`.

6. In Claude Code, type the following prompt:

    ```
    Now the separate final step only: an unknown zone should raise ValueError instead of KeyError. Add a test for it in tests/test_errors.py. Run the tests.
    ```

7. Review the results, noting the following details:

    - The characterization test passes on the untouched code, so it is a safety net for the refactor.
    - The conversion constants now live only in **units.py**, and both adapters call it.
    - The acceptance script turned from four failures to four passes, and you ran it yourself.
    - The zone fix is its own change. A reviewer can tell a unit-handling diff from a zone diff, and a revert of one does not revert the other.

    > **Note**: The hook is configured under `PostToolUse` in **.claude/settings.json**. Whether its output shows on screen depends on your Claude Code version, so verify on your Claude Code version, and rely on Claude's own test runs for what you read.

## Check your work

1. In the second terminal, move up to the lab folder, and run the checker:

    ```
    cd ..
    python check.py
    ```

    > **Note**: The checker needs no API key and no Claude Code. It re-measures the repository, so it does not read anything Claude said.

2. Verify that the last line reads:

    ```
    RESULT: 17/17 checks passed
    ```

3. Type `/exit` to leave Claude Code.

## Clean up

To repeat the lab, copy the **STARTER** folder from the original download over your working copy. Your own work is not needed by any later lab.

## More information

The **SOLUTION** folder holds the finished files. Copy them over a copy of **STARTER** to see the end state, or use them to find a typo. Run `python check.py --workdir <that copy>` to see all 17 checks pass.
