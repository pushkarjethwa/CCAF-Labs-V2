---
lab:
    title: 'Part 5 - Let a CI gate review every pull request'
    module: 'Day 4 - Build-It Assembly'
---

# Part 5 - Let a CI gate review every pull request

This is the signature moment of the assembly. You add a GitHub workflow that runs Claude Code in headless mode on every pull request. Plain code then reads the review and decides whether the pull request may pass. You open three pull requests. A good one passes. A flawed one is blocked, and nobody has to read the diff to see why. A fixed one passes. This part takes about 25 minutes.

The three patches are in the **DATA** folder of the assembly. They are fixed files, so every student gets the same result. The flawed patch contains a fake key, `bb_live_EXAMPLE0000000000000000`, which is not a real credential.

## Understand headless Claude Code

Until now you typed to Claude Code in a session. In CI nobody is there to type. Headless mode runs one prompt, prints the answer and exits. You start it with `-p`, which stands for print.

The review script in this part uses these flags. You do not type them. They live in **.ci/run_review.py**, so the laptop and the CI job use the same ones.

- `-p` runs one prompt and exits.
- `--bare` skips hooks, MCP servers and CLAUDE.md that live in the checkout. This matters because the pull request is untrusted. With `--bare` the key must come from `ANTHROPIC_API_KEY`.
- `--output-format json` prints one JSON envelope instead of text.
- `--json-schema` makes Claude return its findings in a shape the gate can check. The result is in the `structured_output` field.
- `--tools ""` gives the reviewer no tools. It only sees the diff.
- `--allowedTools` is the opposite choice. It lists the tools Claude may use without asking. The review does not need it, so it uses no tools.
- `--max-turns` and `--max-budget-usd` cap how long and how much one review can cost.

Verify on your Claude Code version: run `claude --help` and check that each flag above exists. Names and defaults can change between releases.

1. Run one harmless headless call as a warm-up.

    **Run:**
    ```
    claude -p "Say hello in one line" --output-format json
    ```
    **What it does:** Asks one question without opening a session and prints a JSON envelope.
    **Why we do it here:** It shows what the CI job receives: a JSON object with a `result` field, the cost and a status, not a chat.
    **You should see:** One JSON object. Find the `result` field with a one-line greeting. This call uses your Claude Code sign-in and costs a fraction of a cent.

## Add the workflow and the gate

1. In the **BUILD_IT_ASSEMBLY** folder, add this part's files.

    **Run:**
    ```
    python assemble.py --part 5
    ```
    **What it does:** Copies six files into your repository: the workflow, the review script, the gate, the schema, the review prompt, and a local runner.
    **Why we do it here:** These files are the review gate. The next steps use them locally first and then on GitHub.
    **You should see:** One line that says six files were copied.

2. Move into the repository and start Claude Code.

    **Run:**
    ```
    cd work/brewbean-rewards
    claude
    ```
    **What it does:** Moves into the working repository and starts a session.
    **Why we do it here:** The gate files are now in this repository, so Claude can read them.
    **You should see:** The Claude Code prompt.

3. Ask Claude Code what the gate does.

    **Type in Claude Code:**
    ```
    Read .ci/gate.py and explain in four short lines what exit codes 0, 1, 2 and 3 mean and who decides them.
    ```
    **What it does:** Asks Claude to read the gate and summarize its exit codes.
    **Why we do it here:** You should know what the build will do before it runs: 0 passes, 1 blocks, 2 means the review was not valid structured findings, 3 means there was no review.
    **You should see:** Four short lines. Claude should say the code decides, from parsed fields, and the model only supplies findings.

4. Leave the session.

    **Type in Claude Code:**
    ```
    /exit
    ```
    **What it does:** Closes the Claude Code session.
    **Why we do it here:** The rest of this part happens in the terminal.
    **You should see:** Your terminal prompt.

## Run the gate on your machine first

The local runner builds a diff from a patch file, runs the rule scanner, and then the gate. By default it reads a recorded review, so it needs no key and no network. The recorded reviews are samples written for this course. They are not live model output.

1. Run the gate on the flawed patch. Stay in **work/brewbean-rewards**.

    **Run:**
    ```
    python scripts/run_gate_local.py ../../DATA/pr_flawed.patch
    ```
    **What it does:** Scans the flawed diff, loads a recorded review for it, and runs the gate.
    **Why we do it here:** You see the decision before GitHub is involved, so the pull request later holds no surprises.
    **You should see:** The scanner finds a key-shaped literal, an email in a log call, float points and a missing test. The gate prints BLOCK and `GATE BLOCK (exit 1)`.

2. Run the gate on the good patch.

    **Run:**
    ```
    python scripts/run_gate_local.py ../../DATA/pr_good.patch
    ```
    **What it does:** Does the same for the birthday bonus patch.
    **Why we do it here:** It is the contrast: a clean change gets through.
    **You should see:** The scanner finds nothing. The gate prints PASS and `GATE PASS (exit 0)`.

3. Optional: run a live review of the good patch with your sign-in.

    **Run:**
    ```
    python scripts/run_gate_local.py ../../DATA/pr_good.patch --live --login
    ```
    **What it does:** Calls headless Claude for a real review of the diff and then runs the gate on it.
    **Why we do it here:** It is the same path the CI job uses, with your sign-in instead of the key.
    **You should see:** A line starting with REVIEW DONE, then a gate summary, most likely PASS. A live answer can differ from the recorded one.

    Verify on your Claude Code version: `--login` drops `--bare`, so your hooks and CLAUDE.md may load. The CI job always uses `--bare`.

If you do not have GitHub, stop here and go to the last section of this part.

## Push the workflow to main

The workflow only runs on pull requests that are opened after it exists on **main**, so it goes in first.

1. Commit and push the workflow and the gate.

    **Run:**
    ```
    git add -A
    git commit -m "Add Claude review gate"
    git push origin main
    ```
    **What it does:** Commits the six new files and pushes **main** to GitHub.
    **Why we do it here:** Every pull request from now on is checked by the gate.
    **You should see:** A commit summary that lists six files, then a push to **main**.

2. Confirm that GitHub sees the workflow.

    **Run:**
    ```
    gh workflow list
    ```
    **What it does:** Lists the workflows in the repository.
    **Why we do it here:** It confirms the workflow file is valid enough for GitHub to register.
    **You should see:** A line for **claude-review-gate**, with the state active.

## Pull request 1: the good change

This is the birthday bonus from the plan in Part 1. The patch adds 50 whole points for members, logs the customer id and counts only, and includes tests.

1. Create a branch and apply the patch.

    **Run:**
    ```
    git switch -c feature/birthday-bonus
    git apply ../../DATA/pr_good.patch
    git status --short
    ```
    **What it does:** Makes a branch from **main** and applies the birthday bonus patch to the working files.
    **Why we do it here:** The patch stands in for the work a developer or Claude would do on a feature branch.
    **You should see:** Modified files under **src/rewards** and **tests**.

2. Commit and push the branch.

    **Run:**
    ```
    git add -A
    git commit -m "Add birthday bonus for members"
    git push -u origin feature/birthday-bonus
    ```
    **What it does:** Commits the change and pushes the new branch to GitHub.
    **Why we do it here:** A pull request needs a branch on GitHub.
    **You should see:** Git reports a new branch on the remote.

3. Open the pull request.

    **Run:**
    ```
    gh pr create --base main --title "Add birthday bonus" --body "Members get 50 extra whole points on their birthday."
    ```
    **What it does:** Opens a pull request from the current branch into **main**.
    **Why we do it here:** Opening the pull request starts the review workflow.
    **You should see:** The address of the new pull request.

4. Watch the checks.

    **Run:**
    ```
    gh pr checks --watch
    ```
    **What it does:** Shows the checks on this pull request and refreshes until they finish.
    **Why we do it here:** It is the same information as the Checks tab, in your terminal.
    **You should see:** The check **review** pending for a minute or two, then passing. The command exits when it is done.

    Verify on your GitHub setup: if the check does not start, open the Actions tab of the repository. A workflow that has never run can ask for approval or need Actions to be enabled.

## Pull request 2: the flawed change (the signature moment)

This change is a quick-redeem feature, written the way a rushed change can look. It has a hard-coded key in **config.py**, it logs the customer email, it computes points with a float, and it has no test. Branch from **main**, not from the good branch, so the pull requests stay separate.

1. Create the branch from **main** and apply the flawed patch.

    **Run:**
    ```
    git switch main
    git switch -c feature/quick-redeem
    git apply ../../DATA/pr_flawed.patch
    ```
    **What it does:** Returns to **main**, makes a new branch, and applies the flawed patch.
    **Why we do it here:** Each feature starts from the same base, as it would in a real team.
    **You should see:** No output, and then modified **api.py** and **config.py** in `git status --short`.

2. Commit, push and open the pull request.

    **Run:**
    ```
    git add -A
    git commit -m "Add quick redeem"
    git push -u origin feature/quick-redeem
    gh pr create --base main --title "Add quick redeem" --body "Spend points on drinks in one call."
    ```
    **What it does:** Commits, pushes the branch and opens the pull request.
    **Why we do it here:** The review workflow starts, exactly as it did for the good change.
    **You should see:** The address of the second pull request.

3. Watch the gate stop it.

    **Run:**
    ```
    gh pr checks --watch
    ```
    **What it does:** Follows the checks until they finish.
    **Why we do it here:** This is the moment: the gate runs with no human reading the diff.
    **You should see:** The check **review** finishes with a failure. In GitHub it is a red cross.

4. Read the comment the gate left on the pull request.

    **Run:**
    ```
    gh pr view --comments
    ```
    **What it does:** Prints the pull request and its comments in the terminal.
    **Why we do it here:** The comment is what the author reads. It names the file and line of each blocker.
    **You should see:** A comment titled Claude review gate with the word BLOCK. It lists BLOCKER findings for the hard-coded key, the email in the log and the float points, and a SHOULD_FIX for the missing test. Findings from the scanner say found by scanner. Findings from Claude say found by model.

Why this matters: nobody had to open the diff to catch the key and the email in the logs. The scanner is plain code and catches them with no model. Claude adds judgement on top. The gate, not a person, makes the decision, and it makes it on every pull request, including the ones nobody has time to read.

## Pull request 3: the fixed change

The fixed patch is the same quick-redeem feature done right. It uses whole points, reads its key from the environment, logs the customer id only, and includes tests.

1. Create the branch from **main**, apply the fixed patch, and open the pull request.

    **Run:**
    ```
    git switch main
    git switch -c feature/quick-redeem-fixed
    git apply ../../DATA/pr_fixed.patch
    git add -A
    git commit -m "Add quick redeem, done right"
    git push -u origin feature/quick-redeem-fixed
    gh pr create --base main --title "Add quick redeem (fixed)" --body "Same feature with integer points, a key from the environment, and tests."
    ```
    **What it does:** Builds the third branch and pull request in one go.
    **Why we do it here:** It shows that the gate does not block good work for the same feature.
    **You should see:** The address of the third pull request.

2. Watch the checks.

    **Run:**
    ```
    gh pr checks --watch
    ```
    **What it does:** Follows the checks until they finish.
    **Why we do it here:** The same workflow that blocked the flawed change should now let this one through.
    **You should see:** The check **review** passes.

3. List all three pull requests.

    **Run:**
    ```
    gh pr list
    ```
    **What it does:** Lists the open pull requests.
    **Why we do it here:** It gives you the whole picture in one view.
    **You should see:** Three pull requests: the birthday bonus, the flawed quick redeem and the fixed quick redeem.

4. Optional: read the log of the latest workflow run.

    **Run:**
    ```
    gh run list --limit 3
    gh run view --log
    ```
    **What it does:** Lists recent runs, then asks you to pick one and prints its full log.
    **Why we do it here:** You can see each step, and you can check that the API key was never printed.
    **You should see:** The steps of the job. The key shows as stars if it appears at all.

    Verify on your GitHub CLI version: `gh run view` may ask you to choose a run, or you can add the run number.

## If you do not have GitHub

You can do the whole lesson on your machine. Run the three commands below in **work/brewbean-rewards**. They are the same gate on the same three patches, with recorded reviews.

1. Run all three patches through the local gate.

    **Run:**
    ```
    python scripts/run_gate_local.py ../../DATA/pr_good.patch
    python scripts/run_gate_local.py ../../DATA/pr_flawed.patch
    python scripts/run_gate_local.py ../../DATA/pr_fixed.patch
    ```
    **What it does:** Runs the scanner and the gate on each patch in turn.
    **Why we do it here:** It shows the same three decisions that GitHub shows: pass, block, pass.
    **You should see:** `GATE PASS (exit 0)`, then `GATE BLOCK (exit 1)`, then `GATE PASS (exit 0)`.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 5
    ```
    **What it does:** Checks the six files, the key lines of the workflow, the gate exit codes for the recorded reviews, and that the three patches apply to **main**.
    **Why we do it here:** It gives evidence for the part without needing GitHub or a key.
    **You should see:** `[PASS]` lines and the line ALL PARTS PASS.

## What you just proved

- A workflow on `pull_request` runs a headless Claude review with a key from a secret, and the key is never printed.
- The gate uses parsed fields and exit codes, not words in the text, so its decision is repeatable.
- The scanner catches a secret, an email in a log, and float points with no model at all. The model adds a second opinion.
- A flawed change is stopped by a red check and a comment that names the file and line. A fixed change goes through.
- The workflow uses `pull_request`, not `pull_request_target`. A pull request from a fork cannot reach your secrets, and the PR code is treated as data to read, not as something to trust.
