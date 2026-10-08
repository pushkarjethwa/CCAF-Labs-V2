---
lab:
    title: 'Part 0 - Set up the Brew & Bean workspace'
    module: 'Day 4 - Build-It Assembly'
---

# Part 0 - Set up the Brew & Bean workspace

In this part you create the **brewbean-rewards** repository on your machine, check that its tests pass, and connect it to a throwaway GitHub repository. You also store your API key as a GitHub secret, so the CI review in Part 5 can use it. This part takes about 10 minutes.

You will not write code in any part of this assembly. You run commands and watch Claude Code work.

> **Note**: Never paste a key into a chat, into a file in the repo, or into a command you type. This part shows you ways to pass keys without leaving them in your command history.

## Check your tools

1. Open a terminal in the **BUILD_IT_ASSEMBLY** folder. On Windows, use PowerShell.

2. Check Claude Code.

    **Run:**
    ```
    claude --version
    ```
    **What it does:** Prints the installed Claude Code version.
    **Why we do it here:** Every later part needs the Claude Code command-line tool, so we confirm it is installed before we start.
    **You should see:** A version number.

3. Check Git, the GitHub command-line tool and Python.

    **Run:**
    ```
    git --version
    gh --version
    python --version
    ```
    **What it does:** Prints the version of each tool.
    **Why we do it here:** The assembly uses Git for history, `gh` for GitHub, and Python 3.10 or later for the service and its checks.
    **You should see:** Three version lines. Python must be 3.10 or higher. On macOS or Linux, you may need to type `python3`.

## Create the working repository

The **assemble.py** script builds your working copy from the starting service in **repo_base**. It copies the files, runs `git init`, and makes the first commit on a branch called **main**.

1. Create the repository.

    **Run:**
    ```
    python assemble.py --part 0
    ```
    **What it does:** Copies **repo_base** to **work/brewbean-rewards**, runs `git init`, and makes the first commit on **main**.
    **Why we do it here:** Every part builds on this one small service, so it is the shared starting point for the whole assembly.
    **You should see:** One line that says how many files were copied and that the first commit is on branch main.

2. Move into the new repository and run the service tests.

    **Run:**
    ```
    cd work/brewbean-rewards
    python -m unittest discover -s tests
    ```
    **What it does:** Changes to the repository folder and runs all the unit tests.
    **Why we do it here:** Every later change is judged against a working service, so we confirm the tests pass first.
    **You should see:** Nine tests run and the word OK.

3. Look at the team rules the scanner knows about.

    **Run:**
    ```
    python scripts/check_rules.py --files src/rewards/points.py src/rewards/api.py
    ```
    **What it does:** Scans two files for the four Brew & Bean team rules and prints JSON.
    **Why we do it here:** This key-free scanner is the same one the hook in Part 3 and the CI gate in Part 5 will use.
    **You should see:** A JSON result with a `count` of 0, because the starting service follows every rule.

## Understand workspace trust

The first time you start Claude Code in a folder, it asks whether you trust the files in that folder. Trust matters because a project can carry settings, hooks and commands that run on your machine. If you trust a folder, Claude Code loads those project settings. If you do not, it keeps them off.

1. Start Claude Code in the repository.

    **Run:**
    ```
    claude
    ```
    **What it does:** Starts an interactive Claude Code session in the current folder.
    **Why we do it here:** The trust question appears on the first start in a new folder, and this is the folder you will work in for the next hour.
    **You should see:** A dialog that asks if you trust this folder. Read it, choose the option to trust it (you created this folder a minute ago from files in this package), and then you reach the prompt.

    Verify on your Claude Code version: the wording of the dialog can differ between releases.

2. Leave the session for now.

    **Run:**
    ```
    /exit
    ```
    **What it does:** Closes the Claude Code session.
    **Why we do it here:** The next steps happen in the terminal, and you come back to Claude in Part 1.
    **You should see:** Your normal terminal prompt.

## Create a throwaway GitHub repository

Part 5 opens pull requests, so you need a GitHub repository to push to. Use a new private repository that you can delete afterwards. If you have no GitHub account, skip to the last section of this part.

1. In a browser, sign in to GitHub and create a new **private** repository named **brewbean-rewards-lab**. Do not add a README, a .gitignore or a license. Leave it empty.

2. Create a fine-grained personal access token (PAT).

    - Open your GitHub settings, then **Developer settings**, then **Personal access tokens**, then **Fine-grained tokens**, then **Generate new token**.
    - Give it the name **brewbean-lab** and a short expiry, such as 7 days.
    - Under **Repository access**, choose **Only select repositories** and pick **brewbean-rewards-lab** only.
    - Under **Repository permissions**, set **Contents** to Read and write, **Pull requests** to Read and write, **Workflows** to Read and write, and **Metadata** to Read-only. The Actions secret step also needs **Secrets** to Read and write.
    - Generate the token and copy it. GitHub shows it only once.

    Verify on your GitHub page: permission names and the extra permission needed for secrets can change. If a command later reports a missing permission, add it to the token and generate it again.

3. Save the token in a file that stays outside the repository, such as **token.txt** in your home folder, and then pass it through an environment variable so it never appears in a command you type.

    In PowerShell, run the following commands. The first line asks for the token without showing it.

    **Run:**
    ```
    $env:GH_PAT = Read-Host "Paste the token" -MaskInput
    ```
    **What it does:** Asks for your token with the typing hidden and stores it in an environment variable for this terminal only.
    **Why we do it here:** The token stays out of your command history and out of every file.
    **You should see:** A prompt where nothing is echoed as you paste. If your PowerShell is older, use `Read-Host -AsSecureString` or the file method below.

    In bash on macOS or Linux, run the following command instead.

    **Run:**
    ```
    read -s -p "Paste the token: " GH_PAT; export GH_PAT
    ```
    **What it does:** Reads the token without echoing it and stores it in an environment variable for this terminal only.
    **Why we do it here:** It gives bash users the same history-safe habit.
    **You should see:** A prompt where nothing is echoed as you paste. Press Enter when done.

## Sign in to GitHub from the command line

1. Log in with the token from the environment variable.

    **Run (PowerShell):**
    ```
    $env:GH_PAT | gh auth login --with-token
    ```
    **What it does:** Sends the token to `gh` through standard input, so it is not part of the command line.
    **Why we do it here:** `gh` needs to be signed in to create the repository, push, open pull requests and set secrets.
    **You should see:** No output when it works.

    **Run (bash):**
    ```
    echo "$GH_PAT" | gh auth login --with-token
    ```
    **What it does:** Does the same thing in bash.
    **Why we do it here:** It is the bash form of the PowerShell line above.
    **You should see:** No output when it works.

    If you saved the token in a file instead, you can run `gh auth login --with-token < token.txt`. Delete the file afterwards.

2. Check the login.

    **Run:**
    ```
    gh auth status
    ```
    **What it does:** Shows which account `gh` is signed in as and how.
    **Why we do it here:** It confirms the token works before we push anything.
    **You should see:** A line that says you are logged in to github.com, with your account name.

## Push the repository to GitHub

1. Connect your local repository to the throwaway repository and push **main**. Replace `YOUR-USER` with your GitHub user name.

    **Run:**
    ```
    git remote add origin https://github.com/YOUR-USER/brewbean-rewards-lab.git
    git push -u origin main
    ```
    **What it does:** Adds the empty GitHub repository as the remote called **origin** and pushes your first commit to it.
    **Why we do it here:** Part 5 opens pull requests against this repository, so **main** has to exist there first.
    **You should see:** Git reports that it created the branch **main** on the remote.

    Another way is to let `gh` create the repository from your folder in one step. Use it only if you did not create the repository in the browser: `gh repo create brewbean-rewards-lab --private --source . --push`.

## Store the Anthropic API key as a GitHub secret

The CI review in Part 5 calls Claude from GitHub Actions. It reads the key from a repository secret, so the key never appears in a file or a log.

1. Set the secret. `gh secret set` reads the value from standard input when you do not give one, so it stays out of your history.

    **Run (PowerShell):**
    ```
    $env:ANTHROPIC_API_KEY | gh secret set ANTHROPIC_API_KEY --repo YOUR-USER/brewbean-rewards-lab
    ```
    **What it does:** Saves the value of your `ANTHROPIC_API_KEY` environment variable as an Actions secret in the repository.
    **Why we do it here:** The workflow in Part 5 will use the secret `ANTHROPIC_API_KEY` and never print it.
    **You should see:** A line that says the secret was set.

    **Run (bash):**
    ```
    gh secret set ANTHROPIC_API_KEY --repo YOUR-USER/brewbean-rewards-lab
    ```
    **What it does:** Prompts you for the value and hides your typing. Paste the key and press Enter.
    **Why we do it here:** It stores the key as a repository secret without putting it in your history.
    **You should see:** A prompt for the secret value, then a line that says the secret was set.

    If you have not set the `ANTHROPIC_API_KEY` environment variable yet, your trainer will tell you how to get a key for the lab.

## Verify the part

1. Go back to the **BUILD_IT_ASSEMBLY** folder and run the verification.

    **Run:**
    ```
    cd ../..
    python verify.py --upto 0
    ```
    **What it does:** Checks that the repository exists, is on **main**, has a commit, and that its tests pass.
    **Why we do it here:** It gives you quick evidence that the starting point is right before you build on it.
    **You should see:** A list of `[PASS]` lines and the line ALL PARTS PASS.

## If you do not have GitHub

You can still do Parts 0 to 4 and the lesson of Part 5. Skip the GitHub sections above. In Part 5, you will run the same review gate on your own machine with `python scripts/run_gate_local.py`, which uses recorded reviews and needs no network. You lose only the live pull-request checks.
