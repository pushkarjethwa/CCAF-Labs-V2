---
lab:
    title: 'Part 1 - Explore the codebase and plan a feature'
    module: 'Day 4 - Build-It Assembly'
---

# Part 1 - Explore the codebase and plan a feature

The marketing team of Brew & Bean wants a birthday bonus for members. Before anyone writes code, you use Claude Code to learn the service and to make a plan. You will search the code in two different ways, switch permission modes, ask for deeper thinking, look at your context, and end with a written plan. The feature is planned here and is not built. You build it in Part 5. This part takes about 12 minutes.

## Add the feature request

1. In a terminal in the **BUILD_IT_ASSEMBLY** folder, add this part's file to the repository.

    **Run:**
    ```
    python assemble.py --part 1
    ```
    **What it does:** Copies **docs/BIRTHDAY_BONUS_REQUEST.md** into your working repository.
    **Why we do it here:** It is the written request from marketing that you will point Claude at.
    **You should see:** One line that says one file was copied.

2. Move into the repository and start Claude Code.

    **Run:**
    ```
    cd work/brewbean-rewards
    claude
    ```
    **What it does:** Opens an interactive Claude Code session in the service folder.
    **Why we do it here:** Everything in this part happens inside a session that can see the Brew & Bean code.
    **You should see:** The Claude Code prompt.

## Refer to files with @ and run commands with !

Two small habits save a lot of typing. Type `@` and a path to put a file in the conversation. Start a line with `!` to run a shell command and show its output to Claude.

1. Point Claude at the request.

    **Type in Claude Code:**
    ```
    Read @docs/BIRTHDAY_BONUS_REQUEST.md and summarize it in three bullets.
    ```
    **What it does:** Loads the request file into the conversation and asks for a short summary.
    **Why we do it here:** Claude should plan from the real request, not from your memory of it.
    **You should see:** Three bullets about a 50 point bonus for members on their birthday.

2. Run the tests without leaving the session.

    **Type in Claude Code:**
    ```
    !python -m unittest discover -s tests
    ```
    **What it does:** Runs the tests in your shell and puts the result into the conversation.
    **Why we do it here:** Claude now knows the starting state is green, and you did not need a second terminal.
    **You should see:** Nine tests and the word OK.

## Search by content and search by file name

Claude Code has two search tools, and choosing the right one makes answers faster. The Grep tool searches inside files for text. Use it when you know what the code says. The Glob tool searches for file names that match a pattern. Use it when you know what kind of file you want.

1. Ask a question that is about content.

    **Type in Claude Code:**
    ```
    Where are points rounded or divided? Show the file and line.
    ```
    **What it does:** Makes Claude look for text inside the source files.
    **Why we do it here:** The answer is a line of code, so this is a search by content, which is the Grep tool.
    **You should see:** Claude searches and points to the division in **src/rewards/points.py**. Watch the tool name in the activity line.

2. Ask a question that is about file names.

    **Type in Claude Code:**
    ```
    Which files are tests? List their names only.
    ```
    **What it does:** Makes Claude look for files by name pattern.
    **Why we do it here:** The answer is a list of files, so this is a search by file name, which is the Glob tool.
    **You should see:** Claude lists the three **test_*.py** files. Watch the tool name in the activity line.

## Choose a permission mode

Claude Code works in different modes. In the default mode, it asks before it edits files or runs commands. In plan mode, it can read and think, but it cannot change anything. Press Shift+Tab to cycle through the modes. The bottom of the screen shows the current mode.

1. Switch to plan mode.

    **Type in Claude Code:**
    ```
    /plan
    ```
    **What it does:** Puts the session into plan mode, where Claude only reads and proposes.
    **Why we do it here:** Planning a new feature in a service with money-like points should be a read-only activity.
    **You should see:** The mode label at the bottom changes to plan mode. If `/plan` is not available, press Shift+Tab until you see it.

    Verify on your Claude Code version: the name of the mode and the number of Shift+Tab steps can differ.

## Ask for deeper thinking

Claude can spend more effort before it answers. Recent models decide this on their own, and a request that says to think carefully makes them spend more. You can also check the thinking and effort settings from inside the session.

1. Ask for the plan, and ask for careful thinking.

    **Type in Claude Code:**
    ```
    Think carefully. Using @docs/BIRTHDAY_BONUS_REQUEST.md, plan the birthday bonus. List the files to change, the new tests, and which team rules in @README.md apply. Do not edit anything.
    ```
    **What it does:** Asks for a careful, read-only plan that is grounded in the request and the team rules.
    **Why we do it here:** A plan that you can read costs a few seconds, and a wrong change to points costs real customers.
    **You should see:** A plan that names **src/rewards/api.py**, **src/rewards/points.py** and a new test, and that mentions integer points and not logging the birthday.

    Verify on your Claude Code version: the thinking controls, such as a keyboard toggle or the effort setting, are named differently between releases.

## Look at your context

Everything in the conversation uses space in the model's context window. This includes the files Claude read, the tool results and your messages.

1. Open the context view.

    **Type in Claude Code:**
    ```
    /context
    ```
    **What it does:** Shows how much of the context window is used and what is using it.
    **Why we do it here:** You can see how reading files and searching added to the total, which is why Part 4 will teach you to compact and resume sessions.
    **You should see:** A usage bar and a list of categories, such as messages and tools.

## Save the plan

1. Ask Claude to write down the plan as a short list of steps. It is a plan only.

    **Type in Claude Code:**
    ```
    Give me the final plan as six numbered steps, each one sentence. Do not edit any file.
    ```
    **What it does:** Asks Claude for a short, final version of the plan.
    **Why we do it here:** In Part 5 you will build this feature as a pull request, and a short plan keeps that step small.
    **You should see:** Six numbered steps. They should end with running the tests and the rule scanner.

2. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the session.
    **Why we do it here:** Part 2 starts a fresh session, so it loads the new memory files from the start.
    **You should see:** Your terminal prompt.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 1
    ```
    **What it does:** Checks that the request file is present and that the birthday bonus has not been built yet.
    **Why we do it here:** It confirms the feature is still only a plan, so Part 5 has something to build.
    **You should see:** `[PASS]` lines and the line ALL PARTS PASS.
