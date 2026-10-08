---
lab:
    title: 'Instructor Run Sheet: Demo 5.0, Intro to memory, safeguards and evals'
    module: 'Day 5 - Context, Memory and Reliability'
---

# Instructor Run Sheet: Demo 5.0, Intro to memory, safeguards and evals

This run sheet covers Demo 5.0, which takes about 40 minutes in full, or about 25 minutes on the core path. It uses one story from the first command to the last: Pip, the loyalty-card assistant for a small coffee shop, Brew & Bean. Customers ask Pip about points, rewards and opening hours. You run one small script, `python intro_5_0.py --part N`, five times, and each part adds one idea: conversation, context, memory, safeguards and evals. The demo stands alone: it needs no other Day 5 demo, and every term is explained when it first appears. Demos 5A, 5B and 5C go deeper on the same ideas, and you can mention them as optional practice at the end.

## Core path card

- **The pitch**: Pip forgets, so we resend, save and test. A rule belongs in code. A change needs a score.
- **The one thing students must remember**: Conversation: you resend it. Context: the desk is finite. Memory: a file outside the window. Safeguard: a check in code. Eval: test cases with a score.
- **Full run**: About 40 minutes, with the timings in the steps below.
- **Core path**: About 25 minutes, as in the table.

| Part | Core minutes | Full minutes | What students see |
|---|---|---|---|
| 1. Conversation | 5 | 6 | Pip forgets the name with no history and knows it with history. Input tokens grow |
| 2. Context (shortened) | 1 | 6 | One sentence about the desk. Run the part only if time allows |
| 3. Memory | 6 | 7 | Three facts in a JSON file, a new process, and a correct answer |
| 4. Safeguards | 5 | 7 | The rule as a prompt sentence, then as four lines of code. Skip step D |
| 5. Evals | 6 | 8 | Five cases, v1 and v2, per-case comparison and the `GATE` line |
| 6. Wrap-up | 2 | 2 | The cheat table |

**Optional**:

- **Part 2, context, full run** (6 minutes): Run `python intro_5_0.py --part 2`, or give it one sentence: "The window is a desk of fixed size. When it is full, something has to leave."
- **Part 4, step D, human handoff** (2 minutes): Skip it, and say "odd requests go to a person" in one sentence.

> **Note**: The step headings below show the full-run minutes. On the core path, follow the table above. Every part is a separate command, so you can stop after any part and still have taught a complete idea.

## Before class

1. Run the key-free self-check from this folder, and confirm that it ends with `ALL OK`:

    ```
    python check_offline.py
    ```

    **What it does:** Tests the plain code and runs all five parts against a scripted fake model. **Why we run it here:** It proves the files are intact on your machine. It does not prove anything about the real model.

2. Install the package and set your key:

    ```
    pip install anthropic
    set ANTHROPIC_API_KEY=sk-ant-...
    ```

    **What it does:** Installs the `anthropic` package and sets the key for this terminal (in PowerShell, use `$env:ANTHROPIC_API_KEY="sk-ant-..."`). **Why we run it here:** Parts 1, 3, 4 and 5 call the real model. Part 2 does not need either.

3. Do one live pre-flight of the whole demo, and write your numbers in the notes at the end:

    ```
    python intro_5_0.py --all
    ```

    **What it does:** Runs parts 1 to 5 and the cheat table. **Why we run it here:** Nothing in this demo has been run live yet, so your pre-flight is the first live run. It also tells you what your model says, so you are not surprised in front of the room.

4. Delete the **results** folder contents that the pre-flight wrote, and keep `.gitkeep`:

    ```
    python -c "import pathlib; [p.unlink() for p in pathlib.Path('results').glob('*.json')]"
    ```

    **What it does:** Removes the JSON files that the script wrote. **Why we run it here:** Part 3 should start with no memory file, so the room sees it created.

5. Make the terminal font large. Open **intro_5_0.py** in an editor, next to the terminal.

## Prompts and commands

Type these in this order. Each one is also used in the steps below. Every command has two lines under it: what it does, and why we run it here. Read both out loud for the first few commands, so students learn to ask "why am I running this?".

**Part 1, conversation**

```
python intro_5_0.py --part 1
```

**What it does:** Makes four model calls: one question, the same follow-up with no history, the follow-up again with the history, and one more question. It prints each reply and a table of input tokens.
**Why we run it here:** It shows that the model forgets everything between calls, and that "memory" inside a chat is only your program sending the list again.

The two lines students type (they are in the script between the `TYPE LIVE` markers):

```
messages.append({"role": "assistant", "content": text_of(reply1)})
messages.append({"role": "user", "content": second})
```

**What it does:** The first line adds Pip's earlier reply to the list. The second adds the customer's new question. The list now holds the whole conversation so far.
**Why we run it here:** These two lines are the whole trick of a chat. The model sees the list, so it sees the name.

**Part 2, context**

```
python intro_5_0.py --part 2
```

**What it does:** Prints a bar for each thing on the desk (system prompt, tool definitions, conversation) and a total. It then keeps only the last four messages and prints the bar again, the first message that is left, and whether the name is still on the desk. It makes no model call and needs no key.
**Why we run it here:** It makes the idea of a fixed-size window visible, and it shows what the simplest fix, trimming, costs: a fact that was in an old message is gone.

```
python intro_5_0.py --part 2 --count
```

**What it does:** Does the same, and then asks the API's token-counting endpoint for the real count of the full request.
**Why we run it here:** It compares our rough estimate (characters divided by 4) with the real number. Use it only if you have time.

**Part 3, memory**

```
python intro_5_0.py --part 3
```

**What it does:** Process 1 saves three facts about Maya to **results/memory_C-1042.json** and ends. Then the script starts a second, new Python process. That process starts with an empty messages list, loads the file into the system prompt, and asks Pip a question.
**Why we run it here:** It shows the difference between conversation state, which lives in the program and dies with it, and a memory file, which lives outside and survives.

```
python intro_5_0.py --part 3 --step save
python intro_5_0.py --part 3 --step ask
```

**What it does:** The same two steps as two separate commands.
**Why we run it here:** It lets you stop between the steps and open the file. Use it if you want the room to see the file first.

**Part 4, safeguards**

```
python intro_5_0.py --part 4
```

**What it does:** Step A asks Pip a question with the rule as a sentence in the prompt. Step B prints the four-line `check_limit` function and a table of five requests with what the check says. Step C runs the redeem tool for 80 points with the check in front of it. Step D sorts three requests between Pip and a person.
**Why we run it here:** It shows where a rule lives. A prompt sentence is advice the model reads. A check in code is enforced, because the program runs it before the tool does anything.

**Part 5, evals**

```
python intro_5_0.py --part 5
```

**What it does:** Runs five test cases on prompt v1, grades each reply with plain code, and prints the pass rate. It then runs the same cases on prompt v2, prints the pass rate, a per-case comparison (improved, regressed or same) and a `GATE` line.
**Why we run it here:** It answers "is the new prompt better?" with a score and a rule instead of a feeling.

**Wrap-up**

```
python intro_5_0.py --all
```

**What it does:** Runs all five parts and ends with the cheat table. For a live wrap-up, show the cheat table in **README.md** instead, because the parts have already run.
**Why we run it here:** It is the pre-flight command. The table is the last thing students see.

## Run the demo

### Part 1: Conversation (6 minutes)

1. **(0:00)** Say what Pip is, and run the command:

    ```
    python intro_5_0.py --part 1
    ```

    > **Say**: "Meet Pip. Pip answers questions about points, rewards and opening hours for a coffee shop. Today you will watch five ideas around Pip. The first one is the most surprising: the model remembers nothing."

2. **(1:30)** Read the first two replies. In call 1, Maya says her name. In call 2, the same question has no history.

    > **Say**: "Call 2 asks 'What is my name?' and sends only that one message. Pip cannot know. The model is a function: what you send is all it sees."

    > **Note**: Your model's wording will differ. Say what you see. The expected pattern is that call 2 without history does not give the name.

3. **(3:00)** Open **intro_5_0.py** at the `TYPE LIVE` markers (around line 164). Walk through the two lines, or type them in if you removed them before class:

    ```
    messages.append({"role": "assistant", "content": text_of(reply1)})
    messages.append({"role": "user", "content": second})
    ```

    > **Say**: "These two lines are a chat. We add Pip's earlier answer, then the new question, and we send the whole list. Now the model can see 'I'm Maya'."

    > **Note**: If you removed the two lines to type them live, restore them before you run `python check_offline.py`. The check looks for them.

4. **(4:00)** Point at the token table at the end of the output.

    > **Say**: "Look at the input tokens. Call 1 sends one message. The calls with history send three and five messages, and the token count grows. You pay for the whole list every time. That growth is the next problem."

5. **(5:30)** One sentence to close the part.

    > **Say**: "Conversation: you resend it."

### Part 2: Context (6 minutes, optional on the core path)

1. **(0:00)** Run the command:

    ```
    python intro_5_0.py --part 2
    ```

    > **Say**: "The window is a desk. Three things sit on it: the instructions for Pip, the descriptions of the tools, and the conversation. The desk has a fixed size. Here we use a small desk of 1,000 tokens so the bar is easy to read. Real windows are far bigger, but they are also fixed."

2. **(2:30)** Point at the trim.

    > **Say**: "The simplest fix is to keep only the last four messages. The bar drops. But look at the last line: the name 'Maya' was in a message we dropped, so it is gone."

3. **(4:30)** Point at the two new words.

    > **Say**: "Two words you will hear. Compact means we replace old messages with one short summary. Summarise is how we write that summary. Trimming is easy and loses facts. Next, we keep the facts that matter somewhere else."

    > **Note**: The token numbers are estimates (characters divided by 4). Run `--count` only if you want to show the real count, which needs a key.

4. **(5:30)** One sentence to close the part.

    > **Say**: "Context: the desk is finite."

### Part 3: Memory (7 minutes)

1. **(0:00)** Run the command, and read the first block:

    ```
    python intro_5_0.py --part 3
    ```

    > **Say**: "Maya tells Pip three things that stay true: her name, that she is allergic to nuts, and that she wants no marketing email. We save those three facts to a small JSON file. Then this first process ends, and everything in its memory is gone."

2. **(2:00)** Open **results/memory_C-1042.json**.

    > **Say**: "This is the memory. Three lines of JSON. It is a file on disk, so it is outside the window and outside the process. The file name holds the card number: one customer, one file."

3. **(3:30)** Read the line "--- starting a new Python process ---", and then the second block.

    > **Say**: "Now a new process starts. Its messages list is empty: zero messages. It loads the file, puts the three facts into the system prompt, and asks Pip for the autumn menu by email and a pastry. Pip answers with Maya's name, and respects the nut allergy and the no-email choice."

    > **Note**: Your model's wording will differ. Look for the name, a mention of the allergy or nuts, and no promise to send marketing email. If one is missing, say what you see and move on: the point is where the facts came from.

4. **(5:30)** Close the part.

    > **Say**: "Two kinds of state. The messages list lives in the program and dies with it. A memory file survives a restart. One more thing: keep one customer in one file, so one customer's facts never reach another customer's prompt. Memory: a file outside the window."

### Part 4: Safeguards (7 minutes)

1. **(0:00)** Run the command:

    ```
    python intro_5_0.py --part 4
    ```

    > **Say**: "Pip can redeem points for a reward. The shop has one rule: never redeem more than 100 points in one visit. The question for this part is not whether the rule is good. It is where the rule lives."

2. **(1:00)** Step A: the rule as a prompt sentence.

    > **Say**: "First, the rule is one sentence in the system prompt. The model reads it and, most of the time, follows it. But a sentence is advice. Nothing in the program checks it."

3. **(2:30)** Step B: the code. Read the printed function and the table.

    > **Say**: "Now the same rule in four lines of Python. If the points are above 100, return a handoff. The program runs this before the redeem tool does anything. The table shows five ordinary requests. Fifty, eighty and 100 points are fine. A request for 120 points goes to a person. A gift card is not on the reward list, so the argument check sorts it out too."

    > **Note**: This is not a failure. The table shows the check sorting requests. No request here is an attack or a mistake.

4. **(4:30)** Step C: the tool run with the check in front of it.

    > **Say**: "Here is a real request: 'use 80 points for a pastry'. Pip calls the redeem tool. The line starting `tool call` shows the arguments, and `check: ok` shows our code looked at them first. Then the redeem ran and the balance went from 120 to 40. The model asked for the tool, and the code decided whether it ran."

5. **(5:30)** Step D (full run only): the handoff.

    > **Say**: "Some requests are not for Pip at all: a refund, a complaint, a request to delete data. Plain code looks for those words before any model runs, and puts the request in a queue for a person. Pip answers hours. People handle the rest."

6. **(6:30)** Close the part.

    > **Say**: "A prompt is advice. Code is enforced. Safeguard: a check in code. If the model were fully convinced to ignore the sentence, would the rule still hold? With code, yes."

### Part 5: Evals (8 minutes)

1. **(0:00)** Run the command:

    ```
    python intro_5_0.py --part 5
    ```

    > **Say**: "Someone says 'I improved the prompt'. How do you know? You write test cases. Each one is a question and one thing the answer must contain: a number or a keyword. Five cases here, written by me. Plain Python grades them, with no model."

2. **(2:00)** Read the v1 grade table and the pass rate.

    > **Say**: "Prompt v1 is the first draft. This is its score on the five cases. It is a score, not a feeling. Look at which cases fail and why."

    > **Note**: This is a live run, so your numbers are your own. Say what you see. If v1 already passes all five, say "v1 is already good on these five" and go on; the compare step still works.

3. **(4:00)** Read the line about v2, then the v2 table.

    > **Say**: "Now I change the prompt. Version 2 adds three rules: give the exact number, state the limit when redeeming, and use only the shop facts. Same five cases, same grader."

4. **(5:30)** Read the per-case comparison and the `GATE` line.

    > **Say**: "For each case: improved, regressed or same. A regression is a case that passed before and fails now. An average can hide it, so we look per case. The last line is the gate: ship v2 only if the score is no lower and nothing regressed. PASS or BLOCKED, either one is a real answer."

5. **(7:00)** Read the judge sentence at the end.

    > **Say**: "One more tool exists: an LLM judge, a second model that grades what code cannot, such as tone. Use it when plain code cannot decide. We do not run one today."

6. **(7:30)** Close the part.

    > **Say**: "Eval: test cases with a score."

### Part 6: Wrap-up (2 minutes)

1. **(0:00)** Show the cheat table in **README.md**, or the end of `python intro_5_0.py --all`.

    | Idea | In one line | Practise later (optional) |
    |---|---|---|
    | Conversation | You resend it | Demo 5A, Lab 5.1 |
    | Context | The desk is finite | Demo 5A, Lab 5.1 and the optional Lab 5.4 |
    | Memory | A file outside the window | Demo 5A, Lab 5.1 |
    | Safeguard | A check in code | Demo 5B, Lab 5.2 |
    | Eval | Test cases with a score | Demo 5C, Lab 5.3 |

    > **Say**: "Five ideas. Conversation: you resend it. Context: the desk is finite. Memory: a file outside the window. Safeguard: a check in code. Eval: test cases with a score. If you want to practise any of them, Demos 5A, 5B and 5C go deeper, and Labs 5.1 to 5.3 let you build them. You do not need them to follow today."

## Points to land

- The model remembers nothing. A chat is your program sending the list again, and the list gets longer.
- The window is a fixed-size desk. Trimming is simple and loses facts, so facts that matter live elsewhere.
- A memory file survives a restart. A messages list does not. One customer gets one file.
- A prompt sentence is advice. A check in code is enforced, so a rule that must hold goes in code.
- A change is better only when a fixed set of test cases says so. Compare per case, and use a gate.

## Questions students ask

1. "Why not put everything in one very long prompt?" The window is finite, you pay for every token on every call, and long prompts bury details. A short prompt plus a memory file loaded on demand is cheaper and clearer.

2. "Does the model really remember nothing?" Each API call starts empty. Chat products seem to remember because the app resends the history. The model weights do not change when you talk to it.

3. "What should go in a memory file?" Facts that stay true next month: a name, an allergy, a contact choice. Not small talk, and not one-off events. Part 3 saves only durable facts.

4. "Is it safe to store customer facts?" Store only what you need, one customer per file, and tell the customer. Real systems also add access rules and a way to delete the file. That is a design choice for your organisation.

5. "Why is the rule in code if the prompt already says it?" The prompt is a request. Code is a guarantee. A model can misread a sentence or be talked out of it. A four-line check cannot.

6. "Why five test cases?" Five show the method and keep the demo fast. A real set is larger and mirrors real traffic. Demo 5C uses ten, with provenance and a review queue.

7. "Can the grader be wrong?" Yes. A keyword check is simple. It can pass a wrong answer that contains the keyword, or fail a good answer that uses other words. Start with the simplest grader that works, and add a judge only for what code cannot decide.

## Clean up

Delete the JSON files in the **results** folder to start again. Keep `.gitkeep`:

```
python -c "import pathlib; [p.unlink() for p in pathlib.Path('results').glob('*.json')]"
```

**What it does:** Removes the memory file, the handoff queue and the eval runs. **Why we run it here:** The next class starts with no saved memory, so part 3 shows the file being created.

## Notes after your pre-flight run

Write down the following:

- Part 1, what call 2 without history said: ____________
- Part 1, input tokens for the four calls: ____________
- Part 3, what Pip said about the allergy and the email: ____________
- Part 4, balance after the redeem (expected 40): ____________
- Part 5, pass rate for v1 and for v2 (live): ____________
- Part 5, cases that improved or regressed: ____________
- Part 5, gate result (PASS or BLOCKED): ____________
- Cost line at the end of `--all`: ____________

## More information

- The study guides for these topics are in `STUDENT_V2/STUDY_GUIDES/DAY_5`: `CONTEXT_AND_MEMORY.md`, `RELIABILITY_AND_RESILIENCE.md` and `EVALUATION_AND_PROVENANCE.md`.
- For the file list and what was verified offline, see **README.md** in this folder. Nothing in this demo has been run live yet.
- Practise later (optional, not needed for this demo): Demo 5A (memory), Demo 5B (safeguards) and Demo 5C (evals), and Labs 5.1 to 5.3.
