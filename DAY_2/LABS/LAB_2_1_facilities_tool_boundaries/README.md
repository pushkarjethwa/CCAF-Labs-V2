---
lab:
    title: 'Fix the Tool Boundaries of the Facilities Assistant'
    module: 'Day 2 - Tool Design and MCP'
---

# Fix the tool boundaries of the facilities assistant

In Demo 2A, you watched a retailer's assistant with 12 overlapping tools pick the wrong tool for requests that any person would route correctly. The team did not change the model or the prompt. They measured the problem on 20 prompts, and then fixed the tools in steps: they rewrote the descriptions, consolidated duplicates behind enum parameters, removed what duplicated another tool, and gave each desk only the tools it needs. After every step, the same prompts were sent again and the score was printed. In this lab, you make the same five changes to the campus facilities assistant, and you write five small pieces along the way.

You will complete five pieces of **lab.py**, which add up to 51 lines of code. The lab takes about 35 minutes, and this guide gives you every line. At the end, the assistant has six tools instead of eleven, each desk sees two to four of them, and a gate fails the build if someone adds the old duplicates back.

This lab continues Demo 2A, so you will recognize the following:

- The method: the same prompts every stage, `tool_choice` set to `auto` (never forced), the tool that the model picked graded against the expected one, and a list of confusion pairs after each run.
- The fix order: descriptions first, then consolidation, then removal, then scoping. Each step is cheaper to undo than the next.
- The new failure that scoping brings: if a request lands at a desk that does not have the right tool, it cannot be answered.
- The gate: a change to tools is a code change, and it needs the eval.

The facilities assistant has 11 tools, most with two-word descriptions such as "Look up a room." and "Open a ticket." There are 16 prompts across three desks: workplace booking, the maintenance desk, and the security desk. The eval grades the capability that the chosen tool reaches (for example `room.search` or `ticket.log`), so you may rename and merge tools freely.

## Set up the lab folder

You need Python 3.10 or later and an Anthropic API key.

1. Open a terminal in the **STUDENT_V2/DAY_2/LABS/LAB_2_1_facilities_tool_boundaries** folder.

2. Install the required packages by running the following command:

    ```
    pip install -r requirements.txt
    ```

## Add your Claude API key

1. In the lab folder, create a new file named **.env**.

2. Add the following line to the file, replacing the value with your own API key:

    ```
    ANTHROPIC_API_KEY=sk-ant-your-key-here
    ```

    > **Important**: Never paste your key into chat or commit the **.env** file to git.

3. Save the file, and then test your key by running the following command:

    ```
    python claude_client.py
    ```

4. Verify that you see a short greeting followed by a line that starts with `[usage]`.

## Write the call that every stage uses

In this section, you write the Claude API call with tools. Every stage sends each prompt, together with that stage's tools, through this function.

1. Open **lab.py** in your code editor.

2. Search for the comment **TODO 1 of 5**. Below it is a function named `ask_with_tools`.

3. Replace the line `raise NotImplementedError("TODO 1: call Claude with the tools")  # replace these lines in TODO 1` with the following code. Keep the four-space indent, because the code sits inside the function:

    ```python
        return get_client().messages.create(
            model=model,
            max_tokens=1024,
            system=core.SYSTEM,
            tools=tools,
            tool_choice={"type": "auto"},
            messages=[{"role": "user", "content": prompt}],
        )
    ```

    Noting the following details:

    - `tools` is a list of tool definitions. The model sees only each tool's `name`, `description` and `input_schema`. It never sees your code.
    - `tool_choice={"type": "auto"}` lets the model decide which tool to call, or none. A forced choice is rejected by the 5.5 models, and it would hide the confusion that you are measuring.
    - The reply holds `tool_use` blocks. The harness reads the first one and grades the capability that it reaches.

4. Save the file, and then run the checker:

    ```
    python check.py
    ```

5. Verify that the five **TODO 1** checks pass. The other checks still fail.

## Run stage 1: the baseline

1. Run stage 1 by running the following command:

    ```
    python lab.py --stage 1
    ```

2. Review the output, noting the following details:

    - Each row is one prompt. For each model, it shows the tool that was picked and whether the capability was right.
    - The confusion pairs list what was expected and what was picked. Each pair is a backlog item.
    - The lint line counts structural problems that need no model: descriptions without "when not to use", two tools for one capability, too many tools.
    - Modern models handle many ambiguous tools better than older ones, so the score may already be high. Read the confusion pairs and the lint, and report the real numbers.

## Rewrite the descriptions

In this section, you rewrite the description of each legacy tool. A tool is a small piece of documentation that happens to be executable, so the description is the cheapest lever. Each new description says what the tool does, when to use it, and when not to, and it names the sibling tool to use instead.

1. In **lab.py**, search for the comment **TODO 2 of 5**. Below it is the line `DESCRIPTIONS = {}`.

2. Replace the line `DESCRIPTIONS = {}  # replace these lines in TODO 2` with the following code:

    ```python
    DESCRIPTIONS = {
        "room_lookup": "Read the facts of ONE named room: seating capacity, AV equipment, wheelchair accessibility and which floor it is on. Use when the request names a room such as Harbor 3 or Birch and asks about its facilities. Do NOT use to find rooms that are free (use space_search), to hold or book a room (use reserve_slot or book_room), or for tagged equipment (use asset_lookup).",
        "space_search": "Search for rooms that are free in a time window and match criteria such as minimum seats, whiteboard or floor. Use when no specific room is named and the user wants options to choose from. Do NOT use for facts about one named room (use room_lookup), or to hold or confirm a booking (use reserve_slot or book_room).",
        "find_room": "Resolve ONE room from a partial or misspelled name and return the matching room with its facts. Use when the name given is only approximate, for example 'the big harbor room'. Do NOT use when the exact room name is known (use room_lookup) or to search by time window or capacity (use space_search).",
        "book_room": "Create a confirmed, binding reservation for a named room and time slot, and send calendar invites. Use when the user explicitly wants the booking locked in, confirmed or finalized. Do NOT use for tentative holds or pencil-ins (use reserve_slot), for searching free rooms (use space_search), or for room facts (use room_lookup).",
        "reserve_slot": "Place a tentative hold of about 15 minutes on a named room and slot; it expires by itself and sends no invites. Use when the user wants to pencil a room in while they check with others. Do NOT use for a confirmed reservation (use book_room) or to search for rooms (use space_search).",
        "ticket_create": "Open a NEW repair request for a fault that has no ticket yet, with a summary, a location and a severity. Use when something is broken or faulty, for example a flickering projector. Do NOT use to list existing tickets (use ticket_open), to add a note to a ticket (use maintenance_log), or to look up equipment history (use asset_lookup).",
        "ticket_open": "List every unresolved (open) maintenance ticket for a building. Use when someone asks what is outstanding, unresolved or still open in a building. Do NOT use to create a new ticket (use ticket_create) or to add a note to an existing ticket id (use maintenance_log).",
        "maintenance_log": "Append a work note and labour minutes to an EXISTING ticket id. Use when a technician reports work performed on a ticket such as MT-2291. Do NOT use to open a new ticket (use ticket_create) or to list open tickets (use ticket_open).",
        "asset_lookup": "Look up ONE tagged piece of equipment by asset tag or unit name: warranty expiry, last service date, installed condition and install location. Use when the question is about the history or status of a chiller, projector or other tagged asset. Do NOT use to report a fault (use ticket_create), to find a contractor (use vendor_lookup), or for facts about a room (use room_lookup).",
        "vendor_lookup": "Look up approved vendors and contractors: trade, contact, emergency callout number, approval status and insurance certificate expiry. Use when someone needs to know who the approved contractor is for a trade, or whether a named company is approved and insured. Do NOT use to give a contractor building access (use badge_grant) or to log work (use maintenance_log).",
        "badge_grant": "Grant physical building access to a person for named zones and a date range: new hires, employees changing floors, and visiting technicians or contractors. Use when someone must be able to enter a floor, lab or plant room. Do NOT use to check whether a vendor is approved (use vendor_lookup) or to read room facts (use room_lookup).",
    }
    ```

    Noting the following details:

    - The names and parameters of the tools do not change. Only the descriptions do.
    - `ticket_open` is a misleading name: it lists unresolved tickets, and it does not open one. The description says so.
    - Every "Do NOT use" names the sibling tool to use instead. That is what separates two tools that sound alike.

3. Save the file, run the checker, and then run stage 2:

    ```
    python check.py
    python lab.py --stage 2
    ```

4. Review the output, noting the following details:

    - The lint count rises, because the three description checks now pass. The tool count and the duplicate checks still fail.
    - The definition tokens per request rise too. Better descriptions cost tokens on every request, which is the price of clarity.

## Consolidate the duplicates

In this section, you merge the room tools and the ticket tools into two tools, each with an `action` enum. When two tools do the same kind of operation on a different key, one tool with an enum gives the model one decision instead of four. The binding `book_room` stays separate, because it is the one action that commits a reservation and sends invites.

1. In **lab.py**, search for the comment **TODO 3 of 5**. Below it are the lines `CONSOLIDATED = []` and `CONSOLIDATED_MAP = {}`.

2. Replace the two lines `CONSOLIDATED = []  # replace these lines in TODO 3` and `CONSOLIDATED_MAP = {}` with the following code:

    ```python
    CONSOLIDATED = [
        core.tool(
            "space",
            "Read and hold meeting rooms and spaces. Use when someone wants to find rooms that are free for a time window and match criteria, to read facts about one known room (seating capacity, AV equipment, accessibility, which floor), or to pencil in a tentative hold on a known room. Do NOT use this tool to confirm a reservation or send invites (use book_room), to report broken equipment (use maintenance_ticket), or to look up tagged equipment (use asset_lookup).",
            {"action": {"type": "string", "enum": ["search", "get", "hold"],
                        "description": "search: find free rooms for a time window by minimum seats, whiteboard or floor, when no room is named; get: facts about one named room; hold: tentative auto-releasing hold on a named room, never confirmed"},
             "room": S, "start": S, "end": S, "min_capacity": {"type": "integer"}, "floor": S, "equipment": S},
            ["action"]),
        core.tool(
            "maintenance_ticket",
            "Work with facility repair requests. Use when something is broken and needs a new repair request, when someone wants every unresolved request for a building, or when a technician note or labour minutes must be added to an existing ticket id. Do NOT use this tool to look up warranty or service history of equipment (use asset_lookup), to find a contractor (use vendor_lookup), or to book rooms.",
            {"action": {"type": "string", "enum": ["create", "list_open", "log"],
                        "description": "create: open a new repair request for a fault; list_open: list unresolved requests for a building; log: append a technician note and labour minutes to an existing ticket id"},
             "summary": S, "location": S, "severity": S, "building": S, "ticket_id": S, "note": S, "minutes": {"type": "integer"}},
            ["action"]),
    ]
    CONSOLIDATED_MAP = {
        "space:search": "room.search",
        "space:get": "room.get",
        "space:hold": "room.hold",
        "maintenance_ticket:create": "ticket.create",
        "maintenance_ticket:list_open": "ticket.list_open",
        "maintenance_ticket:log": "ticket.log",
    }
    ```

    Noting the following details:

    - `core.tool(name, description, properties, required)` builds a tool definition in the Messages API shape.
    - The `action` enum gives each operation a name: `search`, `get` and `hold` for rooms, and `create`, `list_open` and `log` for tickets.
    - `CONSOLIDATED_MAP` tells the grader which capability each `tool:action` reaches. When you rename or merge a tool, its map must follow, or the eval grades the wrong thing.

3. Save the file, run the checker, and then run stage 3:

    ```
    python check.py
    python lab.py --stage 3
    ```

4. Review the output, noting the following details:

    - The model now sees 13 tools: the 11 old ones and your two new ones. Adding without removing is the sprawl that makes a toolset worse, and the confusion pairs may show the old and new tools competing.
    - The definition tokens are the highest of all stages.

## Remove the old duplicates

In this section, you remove the seven legacy tools that the two consolidated tools replace. Every tool you keep is a candidate for every request, including requests it has nothing to do with.

1. In **lab.py**, search for the comment **TODO 4 of 5**. Below it is the line `REMOVE = []`.

2. Replace the line `REMOVE = []  # replace this line in TODO 4` with the following code:

    ```python
    REMOVE = ["room_lookup", "space_search", "find_room", "reserve_slot", "ticket_create", "ticket_open", "maintenance_log"]
    ```

    Noting the following details:

    - The removed tools' map entries go too, so the map never points at a tool that does not exist.
    - After this stage the toolset is `space`, `maintenance_ticket`, `book_room`, `asset_lookup`, `vendor_lookup` and `badge_grant`.

3. Save the file, run the checker, and then run stage 4:

    ```
    python check.py
    python lab.py --stage 4
    ```

4. Review the output, noting the following details:

    - All the lint checks now pass: every capability has exactly one route, and no two descriptions say the same thing.
    - The definition tokens fall, and the model has six decisions to make instead of 13.

## Scope the tools per desk

In this section, you give each desk only the tools that it needs. A smaller list makes a wrong pick less likely and cuts the tokens of every request.

1. In **lab.py**, search for the comment **TODO 5 of 5**. Below it is the line `SCOPES = {}`.

2. Replace the line `SCOPES = {}  # replace these lines in TODO 5` with the following code:

    ```python
    SCOPES = {
        "workplace_booking": ["space", "book_room"],
        "maintenance_desk": ["maintenance_ticket", "asset_lookup", "vendor_lookup", "space"],
        "security_desk": ["badge_grant", "vendor_lookup", "space"],
    }
    ```

    Noting the following details:

    - The keys are the three desks that the eval prompts come from.
    - `space` appears in all three desks, because the security desk also asks about rooms, such as how many people the server room holds. If you leave it out, that prompt becomes impossible to answer. That is the new failure that scoping brings.
    - Each desk has two to four tools, and the limit is seven.

3. Save the file, run the checker, and then run stage 5:

    ```
    python check.py
    python lab.py --stage 5
    ```

4. Review the output, noting the following details:

    - The tools offered per request fall to two to four, and the definition tokens fall with them.
    - The progress table at the bottom shows every stage: the score, the tools, the tokens and the lint. The score may not have moved much with a strong model. The tools, the tokens and the lint did.
    - A scope miss means that the right tool was not offered at that desk.

## Run the gate

1. Run the gate by running the following command:

    ```
    python lab.py --stage gate
    ```

2. Review the output, noting the following details:

    - The gate scores the final toolset against the bar (85 percent for the balanced model and 75 percent for the fast model), and it fails on any scope miss or lint failure.
    - A teammate then re-adds three legacy tools. The lint catches it with no model call, because two tools now reach the same capability. A change to tools is a code change, and it needs the eval.

## Check your work

1. Run the checker by running the following command:

    ```
    python check.py
    ```

2. Verify that the last line reads `RESULT: 35/35 checks passed`.

## Troubleshooting

- **`ANTHROPIC_API_KEY` is missing**: Create the **.env** file in the lab folder, as described in the *Add your Claude API key* section.
- **A TODO check fails**: Read the line under the failed check. It names the line to fix. Re-copy the snippet from this guide, keeping the indentation.
- **IndentationError**: A pasted line lost its indent. Code inside a function is indented four spaces.
- **`NotImplementedError` when you run a stage**: TODO 1 is not done yet.
- **Stage 3 shows no new tools**: TODO 3 still holds the starter lines.
- **A prompt is a scope miss in stage 5**: A desk is missing a tool that its prompts need. Check that `space` is in all three desks.
- **A connection error on one call**: Run the stage again.
- **Your scores differ from a classmate's**: This is normal. Models give different answers between runs, and 16 prompts is a small sample. One prompt is more than six points.

## Clean up

The stages save their results in the **evidence** folder. You can delete that folder to start again. Keep your **.env** file private.

## More information

- Demo 2A used a retailer with 12 tools and 20 prompts, and its last step was a validated dispatch that refuses tools outside the desk, bad arguments and double refunds. The old version of this lab, with all the guesswork, is in **_ARCHIVE_before_demo_alignment**.
- The next lab, Lab 2.2, is about what happens after the model picks a tool: the loop, parallel reads, and safe writes.
