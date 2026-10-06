# Break it - Lab 2.1
1. **Forced tool choice.** In `lab.py`, change `tool_choice={"type": "auto"}` to `{"type": "any"}`. Expect a 400 error on the balanced model. Forced choice is not supported on newer models, and it would hide the confusion you are measuring. Restore it.
2. **Scope out the right tool.** Remove `book_room` from `workplace_booking`. Run lab.py: the SCOPE MISS line and check.py fail. Lesson: scoping can cut accuracy as well as help it.
3. **Copy-paste descriptions.** Give two tools the same "Use when" sentence. The lint `no_duplicate_purpose_text` fails, and the confusion list shows the pair.
4. **Dangling map.** Rename a tool without updating `CAPABILITY_MAP`. Lint `capability_map_valid` fails.
