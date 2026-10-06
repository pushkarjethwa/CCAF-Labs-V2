# Day 0: Set up your machine for the labs (about 45 minutes)

Do this before Day 1. It is based on the longer Day 0 pack in `STUDENT/00_DAY0` of the course folder; this version covers what the self-contained labs need and drops the rest. The one extra tool, Claude Code, is only needed from Day 4.

You are done when `python claude_client.py` inside Lab 0.1 prints a greeting and a `[usage]` line.

## What you need

- A laptop: Windows 10/11, macOS 13+, or Ubuntu 20.04+, with 4 GB+ RAM and 5 GB free disk, and permission to install software.
- The **class API key** from the trainer (one-time secure link). It is yours alone and capped at about USD 50.
- Internet access to `api.anthropic.com`, `pypi.org` and `files.pythonhosted.org` on port 443. From Day 2 also `registry.npmjs.org`; from Day 4 also `github.com` and `downloads.claude.ai`.

## Timeline

| Min | Step | Done when |
|---|---|---|
| 0-5 | Section 1: open a terminal in `STUDENT_V2` | `dir` / `ls` shows `requirements.txt` |
| 5-15 | Section 2: Python 3.10+ and the virtual environment | `python --version` shows 3.10+ and the prompt starts with `(.venv)` |
| 15-20 | Section 3: install the packages | the import test prints `imports ok` |
| 20-25 | Section 4: set your API key safely | the length check says `set (N chars)` |
| 25-30 | Section 5: run Lab 0.1's smoke test | a greeting and `[usage]` line appear |
| 30-45 | Sections 6-8: Git, Node, Claude Code (can wait until before Day 2 / Day 4) | each version command prints a version |

## 1. Open a terminal in the lab folder

Unzip the course folder. Open a terminal and go to `STUDENT_V2`.

Windows PowerShell:

```powershell
cd C:\path\to\CCA_F_COMPLETE_TRAINING_PACKAGE\STUDENT_V2
```

macOS / Linux:

```bash
cd /path/to/CCA_F_COMPLETE_TRAINING_PACKAGE/STUDENT_V2
```

## 2. Python and a virtual environment

You need **Python 3.10 or newer**. 3.12 or 3.13 are safe choices. A very new Python can lack ready-made packages and fail to install them.

Windows:

1. Check: `py --list` and `python --version`. If you already have 3.10+, skip to the venv commands.
2. Install from https://www.python.org/downloads/ (tick **Add python.exe to PATH**) or run `winget install Python.Python.3.13`. Open a **new** PowerShell afterwards.
3. Create and activate the environment:

```powershell
py -3.13 -m venv .venv            # or: python -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If activation says "running scripts is disabled": `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`, answer Y, and activate again. CMD users run `.venv\Scripts\activate.bat`.

macOS:

```bash
python3 --version                 # need 3.10+; otherwise: brew install python@3.13
python3 -m venv .venv
source .venv/bin/activate
```

Linux (Ubuntu/Debian):

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
python3 -m venv .venv && source .venv/bin/activate
```

The prompt should now start with `(.venv)`. **Every new terminal needs the activate command again**, and the key again (section 4).

## 3. Install the packages

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import anthropic, dotenv, jsonschema, mcp, httpx2; print('imports ok')"
```

`requirements.txt` holds everything for all labs: `anthropic`, `python-dotenv`, `jsonschema`, `mcp`, `httpx2`, `uvicorn`, `pydantic`. The MCP labs (2.4 and 2.6) need `mcp` 2.x. If `mcp` or `httpx2` fails to install, the other labs still work; tell the trainer.

Behind a company proxy or TLS inspection? Set `HTTPS_PROXY` (and `PIP_CERT` or `SSL_CERT_FILE` for a company certificate) before running pip. If `pip` fails with `CERTIFICATE_VERIFY_FAILED`, that is TLS inspection: ask IT for the company certificate file.

## 4. Set your API key safely

The labs read the key from the environment variable `ANTHROPIC_API_KEY`. They also read a `.env` file (see "Option B").

**Never** put the key in code, chat, e-mail, screenshots or a git repo, and do not type it straight into a command (it lands in your shell history). Hide the terminal while you paste.

### Option A (recommended): this terminal only, hidden input

Windows PowerShell:

```powershell
$sec = Read-Host "Paste class API key (hidden)" -AsSecureString
$env:ANTHROPIC_API_KEY = [System.Net.NetworkCredential]::new("", $sec).Password
Remove-Variable sec
```

macOS / Linux:

```bash
read -rs -p "Paste class API key (hidden): " ANTHROPIC_API_KEY && export ANTHROPIC_API_KEY && echo
```

The key lasts until you close the terminal. Repeat in every new terminal.

Check it without printing it. PowerShell:

```powershell
if ($env:ANTHROPIC_API_KEY) { "set ($($env:ANTHROPIC_API_KEY.Length) chars)" } else { "NOT set" }
```

bash/zsh:

```bash
[ -n "$ANTHROPIC_API_KEY" ] && echo "set (${#ANTHROPIC_API_KEY} chars)" || echo "NOT set"
```

If the length looks wrong, the usual causes are a trailing space or newline, quote marks around the paste, or a cut-off copy.

### Option B: a `.env` file (if retyping is a burden)

Create a file named `.env` in `STUDENT_V2` containing one line: `ANTHROPIC_API_KEY=sk-ant-your-key-here`. The folder's `.gitignore` already excludes `.env`, but do not place `STUDENT_V2` inside a git repo you will push, and do not share the file. Delete it at the end of the course.

### If you think the key leaked

Tell the trainer at once (without pasting the key). They deactivate it and send a new one. Your workspace cap limits any damage.

### Limits to know

- At the cap you see HTTP 400 "You have reached your specified workspace API usage limits". Tell the trainer; do not ask for a second key.
- HTTP 429 means the whole class is calling at once: wait a minute and retry once.

## 5. Smoke test with Lab 0.1

```
cd NEW_LABS\LAB_0_1_hello_claude        # macOS/Linux: cd NEW_LABS/LAB_0_1_hello_claude
python claude_client.py
```

Expected: a short greeting and a line like `[usage] model=... input=... output=... stop_reason=end_turn`. That proves Python, the packages, your key, the network and the model name all work. Then try `python lab.py` and `python check.py` in the same folder if you have time.

## 6. Git and GitHub (needed on Day 4, do it now if you can)

1. Create a GitHub account (https://github.com/signup) and turn on two-factor authentication. Keep recovery codes in a password manager.
2. Install Git: Windows `winget install Git.Git`; macOS `xcode-select --install` or `brew install git`; Linux `sudo apt install git`. Check `git --version`.
3. Set your identity:

```
git config --global user.name  "Your Name"
git config --global user.email "your-id+yourname@users.noreply.github.com"
git config --global init.defaultBranch main
```

4. Install the GitHub CLI (Windows `winget install GitHub.cli`; macOS `brew install gh`; Linux see https://cli.github.com), then `gh auth login` (GitHub.com, HTTPS, browser). Check `gh auth status`.
5. Create a private practice repository **outside** the course folder: `gh repo create ccaf-practice --private --clone --add-readme`. Add a `.gitignore` containing `.env`, `.env.*`, `*.key`, `.venv/`, `__pycache__/`, `evidence/` before anything else.

Before every commit run `git status` and `git diff --staged` and read what you are committing. A key that reaches GitHub, even in a private repo, counts as leaked.

## 7. Node.js (needed on Day 2 for the MCP Inspector and some MCP servers)

Install Node 22 LTS or newer from https://nodejs.org (or `winget install OpenJS.NodeJS.LTS`). Check `node --version` and `npx --version`.

## 8. Claude Code (needed from Day 4)

Install with ONE method. Windows PowerShell: `irm https://claude.ai/install.ps1 | iex`. macOS/Linux: `curl -fsSL https://claude.ai/install.sh | bash`. Open a **new** terminal and check `claude --version` and `claude doctor`.

If Windows says "claude is not recognized", add `%USERPROFILE%\.local\bin` to your user PATH:

```powershell
$bin = "$env:USERPROFILE\.local\bin"
[Environment]::SetEnvironmentVariable("Path", $env:Path + ";$bin", "User")
```

then open a new terminal. In this course Claude Code uses the **class API key**: with `ANTHROPIC_API_KEY` set, start `claude`, approve the key when asked, trust the folder, and type `/status` to confirm the API key is the credential in use. Do not `/login` with a personal subscription during the class, or your usage will not land in the capped class workspace. A free claude.ai plan does not include Claude Code. Install commands change often: if one fails, the official page "Troubleshoot installation and login" wins.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` not found, or opens the Microsoft Store (Windows) | Install Python from python.org with PATH ticked, or use `py -3.13`; turn off "App execution aliases" for python.exe in Windows Settings |
| `No module named venv` (Linux) | `sudo apt install python3-venv` |
| `ModuleNotFoundError: anthropic` (or dotenv, jsonschema) | The virtual environment is not active in this terminal: run the activate command |
| pip fails building a wheel | Use Python 3.12 or 3.13; upgrade pip |
| `python -c "import sys; print(sys.executable)"` points outside `.venv` | Several Pythons: re-activate `.venv` |
| `ANTHROPIC_API_KEY is missing` when running a lab | The key was set in another terminal: redo section 4 here |
| 401 `AuthenticationError` | The key is wrong or revoked: re-copy it exactly; if it persists tell the trainer |
| 404 model not found | A model name is retired or misspelt: set `CLAUDE_MODEL_BALANCED` (or `_FAST`/`_PREMIUM`) to a current model, or unset any override |
| 400 spend limit reached | Your workspace cap is used up: tell the trainer |
| 429 rate limit | Wait 30-60 seconds and retry once |
| `CERTIFICATE_VERIFY_FAILED` | TLS inspection on your network: ask IT for the company certificate and set `SSL_CERT_FILE` / `PIP_CERT` |
| Connection timeout or proxy errors | Set `HTTPS_PROXY`; ask IT to allow the hosts listed under "What you need" |
| Lab 2.4/2.6 cannot import `mcp` or `httpx2` | Re-run `python -m pip install -r requirements.txt`; use Python 3.12 or 3.13 |
| `claude` not recognized | See section 8 PATH fix; open a new terminal |

## What to send the trainer

If anything fails, send the **exact output** of `python --version`, `pip list` (shortened) and the failing command, never the key. Run `python claude_client.py` in Lab 0.1 and send its output once it works.

## Day 0 checklist

- [ ] Python 3.10+ and `.venv` active
- [ ] `pip install -r requirements.txt` finished; import test prints `imports ok`
- [ ] Key set in this terminal (length check passes)
- [ ] `python claude_client.py` in Lab 0.1 prints a greeting and `[usage]`
- [ ] Git, GitHub account with 2FA, `gh auth status` (before Day 4)
- [ ] Node 22+ (before Day 2)
- [ ] Claude Code installed and `/status` shows the API key (before Day 4)
