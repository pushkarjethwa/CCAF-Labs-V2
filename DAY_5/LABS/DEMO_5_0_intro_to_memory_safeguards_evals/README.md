---
lab:
    title: 'Demo 5.0: Intro to memory, safeguards and evals'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Demo 5.0: Intro to memory, safeguards and evals

A small coffee shop, Brew & Bean, has a loyalty card. Customers ask a chat assistant called Pip about their points, the rewards and the opening hours. In this demo you build Pip up in five short parts, and each part adds one idea: the model remembers nothing between calls, so you resend the conversation (conversation). The window it reads has a fixed size (context). Facts that must last go in a file outside the window (memory). A rule that must hold goes in code, not in a prompt (safeguard). A change to the prompt is only an improvement when a set of test cases says so (eval). The whole demo takes about 40 minutes. Every part runs with one small script, `python intro_5_0.py --part N`. The demo stands alone: it needs no other Day 5 demo, and every term is explained when it first appears. Everything works the first time, so this is a tour, not a test. If you have never met these ideas, you leave knowing what each one is and where it lives in code.

## What the demo shows

1. **Conversation** (6 minutes): Pip answers one question. A second question with no history shows that Pip forgets the name. You type two `messages.append` lines, the history goes back in, and Pip knows the name. You print the input tokens of each call and watch them grow.
2. **Context** (6 minutes, key-free): Three things share the desk: the system prompt, the tool definitions and the conversation. A bar shows the budget. You keep only the last four messages and see what is lost. You meet the words compact and summarise.
3. **Memory** (7 minutes): You save three durable facts to a small JSON file, start a new Python process, load the file into the system prompt, and Pip answers with the name, the allergy and the no-email choice.
4. **Safeguards** (7 minutes): The rule "never redeem more than 100 points in one visit" appears first as a prompt sentence. Then it appears as a four-line function that runs before the redeem tool. You also see tool-argument checks and a human handoff for odd requests.
5. **Evals** (8 minutes): Five test cases, each a question and an expected keyword or number, are graded by plain code. You change the system prompt from v1 to v2, run again, compare per case and print a `GATE` line.
6. **Wrap-up** (2 minutes): The cheat table, with a "practise later" column.

## Files in this folder

- **intro_5_0.py**: The demo in one file. Read it top to bottom: the model call, then one section for each part. Run it with `--part N` (1 to 5) or `--all`.
- **data/loyalty_faq.json**: The shop facts: points per dollar, rewards, opening hours and the 100-point limit.
- **data/customer.json**: The customer's card number and points balance.
- **data/sample_chat.json**: A short sample conversation of 12 messages for part 2.
- **data/eval_cases.json**: The five test cases for part 5.
- **data/author_fixtures.json**: Author-written replies that **check_offline.py** uses to test the grader. They are not model results, and the script never reads them.
- **prompts/pip_v1.txt** and **prompts/pip_v2.txt**: The two system prompts for part 5. Version 2 adds three rules.
- **results/**: Files the script writes (the memory file, the handoff queue and the eval runs). It starts empty, with only a `.gitkeep`.
- **check_offline.py**: A key-free self-check that runs every part against a scripted fake model.

## Prerequisites

- Python 3.10 or later: `python --version`.
- The `anthropic` package: `pip install anthropic`.
- `ANTHROPIC_API_KEY` set in your terminal, or in a **.env** file in this folder or a parent folder. Part 2 needs neither.

## Parts table

| Part | Minutes | Idea | You run | Plain result |
|---|---|---|---|---|
| 1 | 6 | Conversation | `python intro_5_0.py --part 1` | Pip forgets the name without history and knows it with history. Input tokens grow |
| 2 | 6 | Context | `python intro_5_0.py --part 2` | A token budget bar, a trim to the last four messages, and what the trim lost |
| 3 | 7 | Memory | `python intro_5_0.py --part 3` | Three facts are saved, a new process loads them, and Pip answers correctly |
| 4 | 7 | Safeguards | `python intro_5_0.py --part 4` | The rule as a prompt sentence, then as code that runs before the tool |
| 5 | 8 | Evals | `python intro_5_0.py --part 5` | A pass rate for v1 and v2, a per-case comparison and a `GATE` line |
| 6 | 2 | Wrap-up | none | The cheat table below |

## The cheat table

| Idea | In one line | Practise later (optional) |
|---|---|---|
| Conversation | You resend it | Demo 5A, Lab 5.1 |
| Context | The desk is finite | Demo 5A, Lab 5.1 and the optional Lab 5.4 |
| Memory | A file outside the window | Demo 5A, Lab 5.1 |
| Safeguard | A check in code | Demo 5B, Lab 5.2 |
| Eval | Test cases with a score | Demo 5C, Lab 5.3 |

## Commands you will meet

Every command has two reasons: what it does, and why we run it here.

| Command | What it does | Why we run it here | Part |
|---|---|---|---|
| `python check_offline.py` | Runs every part against a scripted fake model and prints PASS or FAIL lines | It shows the files and the code are intact before you go live, with no key | first |
| `python intro_5_0.py --part 1` | Makes four model calls and prints the replies and the input tokens | It shows that the model remembers nothing and that history is something you send | 1 |
| `python intro_5_0.py --part 2` | Prints the desk bar, trims the sample chat and shows what was lost. It makes no model call | It shows that the window has a fixed size, and that trimming loses facts | 2 |
| `python intro_5_0.py --part 2 --count` | The same, plus one call to the API's token-counting endpoint | It compares our estimate (characters divided by 4) with the real count | 2 |
| `python intro_5_0.py --part 3` | Saves three facts, then starts a new Python process that loads them and asks Pip a question | It shows that a file outside the window survives a restart | 3 |
| `python intro_5_0.py --part 3 --step save`, then `--step ask` | The same two steps as two separate commands | It lets you stop between the steps and open the memory file | 3 |
| `python intro_5_0.py --part 4` | Shows the rule as a prompt sentence, as code, in a tool run and in a handoff table | It shows where a rule lives, and that code is enforced while a prompt is advice | 4 |
| `python intro_5_0.py --part 5` | Runs five cases on prompt v1 and v2, grades them and prints the gate | It shows how to know that a change helped | 5 |
| `python intro_5_0.py --all` | Runs parts 1 to 5 and then prints the cheat table | One command for the whole demo | all |
| `--model balanced` (add to any command) | Runs Pip on `claude-sonnet-5-5` instead of `claude-haiku-5-5` | The fast model is cheap and enough for Pip. The main model shows that the lessons do not depend on the model | all |

## Run the demo

1. Run the key-free self-check from this folder, and confirm that it ends with `ALL OK`:

    ```
    python check_offline.py
    ```

    **What it does:** Tests the rule, the grader, the gate and the memory file, and runs all five parts against a scripted fake model. **Why we run it:** It tells you the files are correct before you go live, so any surprise comes from the real model and not from the files.

2. Run a part, then the next ones in order:

    ```
    python intro_5_0.py --part 1
    ```

    **What it does:** Runs part 1 with the real model. **Why we run it:** Each part is a short, separate run, so you can stop and read between parts.

3. Run the parts one at a time, using the commands in the parts table above. Read the output of each part before you move to the next. The commands table above says what each command does and why.

## What to expect

The model's wording differs on every run, so describe what you see. These patterns are what the demo is built around:

- In part 1, the call without history does not know the name, and the call with history does. The input tokens rise from call to call.
- In part 3, Pip mentions the name, the nut allergy or the no-email choice, because the saved facts are in its system prompt.
- In part 4, the check table is the same on every run, because it is plain code.
- In part 5, the per-case comparison and the `GATE` line come from your live run. They can be PASS or BLOCKED, and either one is a real result.

What is verified offline: the files and data, the rule and the argument checks, the router, the grader, the per-case comparison and the gate, the memory file and the new-process step, and all five parts against a scripted fake model. The fake model replays author-written replies from **data/author_fixtures.json**, so the offline pass rates (60 percent and 100 percent) test the code. They are not model results. Nothing in this demo has been run live yet, so your first run is the first live run. The token numbers in part 2 are estimates unless you add `--count`.

## Design notes

- **One story, five ideas.** Pip never changes. Each part adds one idea to the same small assistant.
- **The rule appears twice in part 4.** First as a prompt sentence, then as four lines of code. The point is where the rule lives, and every request in that part runs normally.
- **The memory step starts a real new process.** `--part 3` runs the save step, then launches `python intro_5_0.py --part 3 --step ask` as a separate process. Its messages list is empty, so only the file can carry the facts.
- **The grader is plain code.** A reply passes when it contains the expected keyword or number. An LLM judge is mentioned in one sentence in part 5 and is not run.
- **Costs are small.** Pip runs on the fast model, and the whole demo makes about 18 short calls.

## More information

- This demo stands alone. Run it before Lab 5.1 if you are new to these ideas.
- Practise later (optional, not needed for this demo): Demo 5A and Lab 5.1 go deeper on memory and context, Demo 5B and Lab 5.2 on safeguards, and Demo 5C and Lab 5.3 on evals.
