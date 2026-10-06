"""YOUR working toolset. main.py scores this file as the 'after' result.

You edit three things below:
  TOOLS           the tool definitions the model sees (name, description, input_schema)
  CAPABILITY_MAP  tool name, or "tool:action" for tools with an `action` enum -> capability id
                  (keep it honest: the eval grades the capability reached, see DATA/capabilities.json)
  SCOPES          task context -> names of the tools offered in that context (<= 7 each)

Only name / description / input_schema are sent to the API.
"""
from toolset_original import CONTEXTS, LEGACY_MAP, LEGACY_TOOLS

# TODO(student) D1: rewrite every description - when to use AND when NOT to use (name the sibling tool to use instead).
# TODO(student) D2: consolidate overlapping tools, e.g. one `space` tool with action = search | get | hold.
# TODO(student) D3: prune tools that duplicate another tool's purpose.
TOOLS = [dict(t) for t in LEGACY_TOOLS]

# TODO(student) D4: update the map for every tool you rename, merge or remove ("space:search" -> "room.search" ...).
CAPABILITY_MAP = dict(LEGACY_MAP)

# TODO(student) D5: scope toolsets per task context (<= 7 tools each; keep what that desk really needs).
SCOPES = {ctx: [t["name"] for t in TOOLS] for ctx in CONTEXTS}
