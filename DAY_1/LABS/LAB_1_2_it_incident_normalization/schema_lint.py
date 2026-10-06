"""Offline schema linter for structured-output schemas (VERIFIED_API_FACTS section 3).  ⚠ VERSION-SENSITIVE (verified 2026-10-03)

    python schema_lint.py versions/v1.schema.json          # prints issues, exit 1 if any
    from schema_lint import lint; issues = lint(schema_dict)

Run it on your schema file; it is an offline linter, no API key needed.
Rules (each issue is one line, prefixed with the JSON path):
  * every object schema has additionalProperties: false
  * no keyword the grammar does not support (min/max/length/uniqueItems/... see UNSUPPORTED)
  * nullable fields use anyOf [{type: X}, {type: "null"}] - never "type": ["string", "null"]
  * required-but-nullable: every property of an object is listed in `required` (no optional fields)
  * enums match the contract in DATA/target_schema.json (no drift such as "Sev-3" / "P4")
  * string formats only from the supported list; <= 16 union types, <= 24 optional params
"""
import json
import pathlib
import sys

UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
               "uniqueItems", "maxItems", "minProperties", "maxProperties", "patternProperties", "propertyNames",
               "contains", "minContains", "maxContains", "not", "if", "then", "else", "oneOf", "dependentRequired",
               "dependentSchemas", "unevaluatedProperties", "unevaluatedItems"}
FORMATS = {"date", "email", "date-time", "ipv4", "uri", "duration", "ipv6", "hostname", "time", "uuid"}
TARGET = pathlib.Path(__file__).resolve().parent / "data" / "target_schema.json"


def _walk(node, path, issues, counters):
    if isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, f"{path}[{index}]", issues, counters)
        return
    if not isinstance(node, dict):
        return
    for key in node:
        if key in UNSUPPORTED:
            issues.append(f"{path}: unsupported keyword '{key}' (move the rule into the prompt or a post-validation step)")
    node_type = node.get("type")
    if isinstance(node_type, list):
        issues.append(f"{path}: 'type' is an array {node_type}; use anyOf [{{type: X}}, {{type: \"null\"}}]")
    if "$ref" in node and not str(node["$ref"]).startswith("#"):
        issues.append(f"{path}: external $ref is not supported")
    if "format" in node and node["format"] not in FORMATS:
        issues.append(f"{path}: format '{node['format']}' is not in the supported list")
    if "anyOf" in node:
        counters["unions"] += 1
    if node_type == "object" or "properties" in node:
        props = node.get("properties", {})
        if node.get("additionalProperties") is not False:
            issues.append(f"{path}: object must set additionalProperties: false")
        missing = [prop for prop in props if prop not in node.get("required", [])]
        for prop in missing:
            counters["optional"] += 1
            issues.append(f"{path}.{prop}: property is not in 'required' (use required-but-nullable, not optional)")
    for key, value in node.items():
        if key in ("properties", "$defs", "definitions") and isinstance(value, dict):
            for name, sub in value.items():
                _walk(sub, f"{path}.{name}" if path != "$" else f"$.{name}", issues, counters)
        elif key in ("items", "anyOf", "allOf"):
            _walk(value, f"{path}.{key}", issues, counters)


def lint(schema: dict, target: dict | None = None) -> list[str]:
    issues: list[str] = []
    counters = {"unions": 0, "optional": 0}
    _walk(schema, "$", issues, counters)
    if counters["unions"] > 16:
        issues.append(f"$: {counters['unions']} union types (limit 16 per request)")
    if counters["optional"] > 24:
        issues.append(f"$: {counters['optional']} optional parameters (limit 24 per request)")
    target = target if target is not None else json.loads(TARGET.read_text(encoding="utf-8"))
    props = schema.get("properties", {})
    for name in target["properties"]:
        if name not in props:
            issues.append(f"$.{name}: property from the contract is missing")
    for name in ("severity", "category"):
        want, got = target["properties"][name]["enum"], props.get(name, {}).get("enum")
        if got is None:
            issues.append(f"$.{name}: no enum")
        elif set(got) != set(want):
            issues.append(f"$.{name}: enum drift - extra {sorted(set(got) - set(want))} missing {sorted(set(want) - set(got))}")
    return issues


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    issues = lint(json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")))
    for issue in issues:
        print("LINT:", issue)
    print("LINT CLEAN" if not issues else f"{len(issues)} lint issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
