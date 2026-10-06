# How the lab code works

Never used the Anthropic SDK before? Read this page first. It takes five minutes.

## 1. The 60-second picture

```
your lab.py  --->  claude_client.py  --->  Anthropic SDK  --->  Claude API  --->  Claude
   (your logic)    (one small file)        (python package)     (the internet)    (the model)
```

- `lab.py` is the file you edit. It holds the exercise.
- `claude_client.py` is the only file that talks to Claude. Every lab folder has its own copy. Open it. It is about 70 lines.
- Nothing is hidden in a shared folder. If you can see the lab folder, you can see all the code.

## 2. Where is each thing? (open `claude_client.py`)

| I want to see... | Look here |
|---|---|
| Where the API key is read | `get_client()` (checks `ANTHROPIC_API_KEY`) |
| Where the SDK client is created | `get_client()` (`anthropic.Anthropic()`, created once on first use) |
| Where a message is sent to Claude | `ask()` -> the line `get_client().messages.create(**request)` |
| Where the answer text is read | `text_of()` |
| Where tool requests are read | `tool_calls_of()` |
| Where token usage is printed | `print_usage()` |
| Which models the lab uses | `MODEL_FAST`, `MODEL_BALANCED`, `MODEL_PREMIUM` |

## 3. Set up your key (once)

1. Get an API key from the Anthropic Console.
2. In the lab folder (or its parent), create a file named `.env` with one line:
   ```
   ANTHROPIC_API_KEY=sk-ant-your-key-here
   ```
3. Never share the key, paste it in chat, or commit `.env` to git.
4. Test: `python claude_client.py`. You should see a short greeting and a `[usage]` line.

If the key is missing you get a clear message and the program stops. There is no fake model: labs talk to real Claude. A few labs also have parts that run without a key (they check your own code on saved sample data). Each lab README says which.

## 4. Anatomy of one API call

Request (what you send):

| Field | Meaning |
|---|---|
| `model` | Which Claude model answers |
| `max_tokens` | Hard limit on the answer length. Required |
| `system` | Standing instructions for the whole conversation |
| `messages` | The conversation so far: a list of `{"role": "user" or "assistant", "content": ...}` |
| `tools` | Optional list of tools Claude may ask you to run |

Response (what you get back):

| Field | Meaning |
|---|---|
| `content` | A list of blocks. Usually a `text` block. With tools it can also hold `tool_use` blocks |
| `stop_reason` | Why Claude stopped: `end_turn` (done), `tool_use` (wants a tool), `max_tokens` (cut off) |
| `usage` | `input_tokens` and `output_tokens`. This is your cost |

## 5. How a lab folder is organised

```
LAB_x_y_name/
  README.md           what you will build, goal, time, how to run
  lab.py              the file you edit; numbered steps; TODOs marked "TODO 1", "TODO 2"
  claude_client.py    the only file that talks to Claude (read it once)
  data/               the lab's input files
  check.py            run after lab.py; prints PASS or FAIL
  BREAK_IT.md         deliberate failures to try
  CHALLENGE.md        stretch goals
```

Read `lab.py` from top to bottom. Each step is a short function with a comment saying why.

## 6. Common errors

| You see | Fix |
|---|---|
| `ANTHROPIC_API_KEY is missing` | Create `.env` as in section 3 |
| `AuthenticationError` | The key is wrong or revoked. Make a new one |
| `NotFoundError` ... model | The model name is retired or misspelt. Set `CLAUDE_MODEL_BALANCED` to a current model |
| `BadRequestError` ... max_tokens | Always pass `max_tokens`. If answers are cut off, raise it |
| `BadRequestError` ... tool_result | Every `tool_use` needs a matching `tool_result` with the same id, in the next user message |
| `RateLimitError` | Wait a minute and retry |

## 7. Glossary

- **Token**: a chunk of text (about 4 characters). You pay per token.
- **Model alias**: our names `MODEL_FAST`, `MODEL_BALANCED`, `MODEL_PREMIUM` for small, medium and large models.
- **stop_reason**: why the answer ended.
- **Tool**: a function you describe to Claude. Claude asks to call it; your code runs it.
- **tool_use / tool_result**: Claude's request to run a tool / your reply with the output.
- **Schema**: a description of the exact shape of data (field names and types).
- **Prompt cache**: reusing an unchanged beginning of a prompt at a lower price.
- **Batch**: sending many requests together to be processed later at a lower price.
