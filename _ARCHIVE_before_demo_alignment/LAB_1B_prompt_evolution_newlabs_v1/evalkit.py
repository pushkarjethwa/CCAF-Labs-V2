"""evalkit.py - the evaluation toolkit for the prompt-evolution lab. GIVEN: read it, do not edit.

Parts, top to bottom (no Claude call anywhere in this file):
  1. DOCS         load the 12 messy invoices, ground truth and few-shot example material
  2. PARSING      strict vs loose JSON parsing (report both: a loose parser hides a missing format contract)
  3. PROMPT FILES a prompt version is a FILE: === SYSTEM === / === USER === with a {{document}} placeholder
  4. SCORING      field-level scorer: strict on purpose, because accounting systems are strict
  5. LEAK CHECK   detects few-shot example values that leak into unrelated documents
  6. CHECKS       semantic validation that needs no ground truth (arithmetic, signs, date order)
  7. SCHEMA AUDIT static audit of a JSON Schema against the structured-output limits
  8. REPORT       the projector-friendly tables
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import jsonschema

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
PROMPTS_DIR = HERE / "prompts"

# ---------------------------------------------------------------- 1. DOCS
FIELDS = ["invoice_number", "vendor", "invoice_date", "due_date", "currency",
          "subtotal", "tax", "total", "line_items", "po_number"]
NULLABLE_FIELDS = ["due_date", "po_number"]


@dataclass(frozen=True)
class Doc:
    doc_id: str
    text: str
    truth: dict


def load_docs(data_dir: Path | None = None) -> list[Doc]:
    root = Path(data_dir) if data_dir else DATA_DIR
    truth = json.loads((root / "ground_truth.json").read_text(encoding="utf-8"))
    docs = []
    for doc_id in sorted(truth):
        text = (root / "docs" / f"{doc_id}.txt").read_text(encoding="utf-8")
        docs.append(Doc(doc_id, text, truth[doc_id]))
    return docs


def load_examples(data_dir: Path | None = None) -> dict[str, tuple[str, dict]]:
    """name -> (input_text, output_record)."""
    root = Path(data_dir) if data_dir else DATA_DIR
    outputs = json.loads((root / "examples" / "examples.json").read_text(encoding="utf-8"))
    return {name: ((root / "examples" / f"{name}.txt").read_text(encoding="utf-8"), record) for name, record in outputs.items()}


# ---------------------------------------------------------------- 2. PARSING
def parse_json_loose(text: str):
    """Parse JSON, tolerating a ```json fence or a sentence before/after it. Raises ValueError if no JSON object is found."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    for candidate in (cleaned, cleaned[cleaned.find("{"):cleaned.rfind("}") + 1] if "{" in cleaned else ""):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    raise ValueError("no JSON object found in model output")


@dataclass
class ParseResult:
    obj: dict | None
    strict_ok: bool
    loose_ok: bool
    error: str = ""


def parse_response(raw: str) -> ParseResult:
    text = (raw or "").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return ParseResult(obj, True, True)
        return ParseResult(None, False, False, "top-level JSON is not an object")
    except json.JSONDecodeError:
        pass
    try:
        obj = parse_json_loose(text)
    except ValueError as error:
        return ParseResult(None, False, False, str(error))
    if not isinstance(obj, dict):
        return ParseResult(None, False, False, "top-level JSON is not an object")
    return ParseResult(obj, False, True, "needed fence/prose stripping")


# ---------------------------------------------------------------- 3. PROMPT FILES
DOC_TOKEN = "{{document}}"
_SYS, _USER = "=== SYSTEM ===", "=== USER ==="


@dataclass(frozen=True)
class PromptVersion:
    version: str
    system: str
    user_template: str
    schema: dict | None = None        # sent via output_config.format when not None
    parent: str | None = None
    status: str = "candidate"
    change: str = ""
    sha256: str = ""
    path: str = ""

    def render(self, doc_text: str) -> dict:
        """-> keyword arguments for ask(): messages, optional system, and output_config when the version carries a schema."""
        request_kwargs: dict = {"messages": [{"role": "user", "content": self.user_template.replace(DOC_TOKEN, doc_text)}]}
        if self.system:
            request_kwargs["system"] = self.system
        if self.schema is not None:
            request_kwargs["output_format"] = {"type": "json_schema", "schema": self.schema}  # becomes output_config.format in demo.py
        return request_kwargs

    @property
    def full_text(self) -> str:
        return f"{self.system}\n{self.user_template}"


def parse_prompt_text(raw: str) -> tuple[str, str]:
    raw = raw.replace("\r\n", "\n")
    if _SYS not in raw or _USER not in raw:
        raise ValueError(f"prompt file must contain '{_SYS}' and '{_USER}' sections")
    head, user = raw.split(_USER, 1)
    system = head.split(_SYS, 1)[1]
    user = user.strip("\n")
    if DOC_TOKEN not in user:
        raise ValueError(f"user section must contain the {DOC_TOKEN} placeholder")
    return system.strip("\n"), user


def load_prompt_file(path: Path, version: str | None = None, schema: dict | None = None, **meta) -> PromptVersion:
    path = Path(path)
    raw = path.read_bytes()
    system, user = parse_prompt_text(raw.decode("utf-8"))
    return PromptVersion(version or path.stem, system, user, schema, sha256=hashlib.sha256(raw).hexdigest(),
                         path=str(path), **meta)


def load_vault_meta(prompts_dir: Path | None = None) -> dict:
    directory = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
    return json.loads((directory / "vault.json").read_text(encoding="utf-8"))


def load_schema(prompts_dir: Path | None = None) -> dict:
    directory = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
    meta = load_vault_meta(directory)
    return json.loads((directory / meta["schema"]).read_text(encoding="utf-8"))


def load_versions(prompts_dir: Path | None = None, include_ablations: bool = False) -> dict[str, PromptVersion]:
    directory = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
    meta = load_vault_meta(directory)
    schema = load_schema(directory)
    versions: dict[str, PromptVersion] = {}
    for entry in meta["versions"]:
        if entry["status"] == "ablation" and not include_ablations:
            continue
        versions[entry["version"]] = load_prompt_file(directory / entry["file"], entry["version"],
                                                      schema if entry["output_schema"] else None,
                                                      parent=entry["parent"], status=entry["status"], change=entry["change"])
    return versions


# ---------------------------------------------------------------- 4. SCORING
NUMERIC = ("subtotal", "tax", "total")


def _norm_str(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().strip(".,;:").casefold()


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", str(text).casefold()))


def _item_match(predicted: dict, truth_item: dict) -> bool:
    if not isinstance(predicted, dict):
        return False
    if not (_is_num(predicted.get("qty")) and _is_num(predicted.get("unit_price"))):
        return False
    if abs(predicted["qty"] - truth_item["qty"]) > 0.005 or abs(predicted["unit_price"] - truth_item["unit_price"]) > 0.005:
        return False
    predicted_tokens, truth_tokens = _tokens(predicted.get("description", "")), _tokens(truth_item["description"])
    return bool(truth_tokens) and len(predicted_tokens & truth_tokens) / len(truth_tokens) >= 0.6


def score_line_items(pred, truth: list) -> float:
    if not isinstance(pred, list) or not pred:
        return 0.0
    remaining = list(pred)
    matched = 0
    for truth_item in truth:
        for index, predicted_item in enumerate(remaining):
            if _item_match(predicted_item, truth_item):
                matched += 1
                remaining.pop(index)
                break
    return matched / max(len(truth), len(pred))


def score_field(name: str, pred, truth) -> float:
    if name == "line_items":
        return score_line_items(pred, truth)
    if truth is None:
        return 1.0 if pred is None else 0.0
    if pred is None:
        return 0.0
    if name in NUMERIC:
        return 1.0 if _is_num(pred) and abs(pred - truth) <= 0.005 else 0.0
    if name in ("invoice_date", "due_date"):
        return 1.0 if isinstance(pred, str) and pred.strip() == truth else 0.0
    if name == "currency":
        return 1.0 if isinstance(pred, str) and pred.strip().upper() == truth else 0.0
    return 1.0 if isinstance(pred, (str, int, float)) and _norm_str(pred) == _norm_str(truth) else 0.0


@dataclass
class DocScore:
    doc_id: str
    parsed: bool
    strict_parsed: bool
    fields: dict[str, float] = field(default_factory=dict)

    @property
    def accuracy(self) -> float:
        return sum(self.fields.values()) / len(FIELDS) if self.fields else 0.0


def score_doc(doc_id: str, pred: dict | None, truth: dict, *, strict_parsed: bool = False) -> DocScore:
    if not isinstance(pred, dict):
        return DocScore(doc_id, False, False, {name: 0.0 for name in FIELDS})
    fields = {name: (score_field(name, pred[name], truth[name]) if name in pred else 0.0) for name in FIELDS}
    return DocScore(doc_id, True, strict_parsed, fields)


@dataclass
class Summary:
    n_docs: int
    parse_rate: float            # loose parse (fence/prose tolerated)
    strict_parse_rate: float     # json.loads on the raw text
    accuracy: float              # micro mean over docs x fields
    per_field: dict[str, float]
    null_handling: float         # truth-null slots answered with JSON null
    null_slots: int
    null_hits: int
    false_nulls: int             # truth non-null slots answered with null


def summarize(scores: list[DocScore], truths: dict[str, dict], preds: dict[str, dict | None]) -> Summary:
    n = len(scores)
    per_field = {name: sum(doc_score.fields[name] for doc_score in scores) / n for name in FIELDS}
    slots = hits = false_nulls = 0
    for doc_score in scores:
        truth, pred = truths[doc_score.doc_id], preds.get(doc_score.doc_id)
        for name in NULLABLE_FIELDS:
            answered_null = isinstance(pred, dict) and name in pred and pred[name] is None
            if truth[name] is None:
                slots += 1
                hits += 1 if answered_null else 0
            elif answered_null:
                false_nulls += 1
    return Summary(n, sum(doc_score.parsed for doc_score in scores) / n, sum(doc_score.strict_parsed for doc_score in scores) / n,
                   sum(doc_score.accuracy for doc_score in scores) / n, per_field,
                   hits / slots if slots else 1.0, slots, hits, false_nulls)


# ---------------------------------------------------------------- 5. LEAK CHECK
LEAK_FIELDS = ["invoice_number", "vendor", "po_number", "due_date", "invoice_date"]
_EX = re.compile(r"<example>\s*<input>(.*?)</input>\s*<output>(.*?)</output>\s*</example>", re.S)


def extract_examples(prompt_text: str) -> list[tuple[str, dict]]:
    """[(example_input_text, example_output_dict)] found in a prompt's <example> blocks."""
    examples = []
    for example_input, example_output in _EX.findall(prompt_text):
        try:
            examples.append((example_input.strip(), json.loads(example_output.strip())))
        except json.JSONDecodeError:
            continue
    return examples


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.casefold()))


def template_similarity(a: str, b: str) -> float:
    """Jaccard overlap of alphabetic word sets - a crude 'same template family' signal."""
    words_a, words_b = _words(a), _words(b)
    return len(words_a & words_b) / len(words_a | words_b) if words_a | words_b else 0.0


@dataclass(frozen=True)
class Leak:
    doc_id: str
    field: str
    value: str
    example_index: int


def _norm(value) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().casefold()


def find_leaks(doc_id: str, pred: dict | None, truth: dict, examples: list[tuple[str, dict]]) -> list[Leak]:
    if not isinstance(pred, dict):
        return []
    leaks = []
    for example_index, (_, example_record) in enumerate(examples):
        for field_name in LEAK_FIELDS:
            example_value, predicted_value = example_record.get(field_name), pred.get(field_name)
            if example_value is None or predicted_value is None:
                continue
            if _norm(predicted_value) == _norm(example_value) and _norm(predicted_value) != _norm(truth.get(field_name)):
                leaks.append(Leak(doc_id, field_name, str(predicted_value), example_index))
    return leaks


# ---------------------------------------------------------------- 6. CHECKS (semantic, no ground truth needed)
@dataclass
class Issue:
    path: str
    kind: str
    expected: str
    received: str
    message: str


def validate(obj, schema) -> list[Issue]:
    """JSON Schema validation (the structural layer). Returns a list of Issue."""
    validator = jsonschema.validators.validator_for(schema)(schema)
    return [Issue("$." + ".".join(str(p) for p in err.absolute_path), "schema", str(err.validator), str(err.instance)[:80], err.message[:120])
            for err in validator.iter_errors(obj)]


AMBIGUOUS_DATE = re.compile(r"(?<![\d/.\-])(\d{1,2})([/.\-])(\d{1,2})\2(\d{4})(?![\d/.\-])")


def has_ambiguous_date(text: str) -> bool:
    """True if the document prints a numeric date whose day/month can be swapped (both <= 12, different)."""
    for match in AMBIGUOUS_DATE.finditer(text):
        first, second = int(match.group(1)), int(match.group(3))
        if first <= 12 and second <= 12 and first != second:
            return True
    return False


def _issue(path: str, expected: str, received, msg: str) -> Issue:
    return Issue(path=path, kind="semantic", expected=expected, received=str(received)[:120], message=msg)


def _iso(value) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def semantic_issues(pred: dict, *, tol: float = 0.02) -> list[Issue]:
    issues: list[Issue] = []
    try:
        subtotal, tax, total = float(pred["subtotal"]), float(pred["tax"]), float(pred["total"])
    except (KeyError, TypeError, ValueError):
        return [_issue("subtotal/tax/total", "numbers", "missing or non-numeric", "cannot run arithmetic checks")]
    if abs(subtotal + tax - total) > tol:
        issues.append(_issue("total", f"{subtotal + tax:.2f}", total, "subtotal + tax != total"))
    items = pred.get("line_items") or []
    try:
        line_sum = sum(float(item["qty"]) * float(item["unit_price"]) for item in items)
    except (KeyError, TypeError, ValueError):
        line_sum = None
    if line_sum is not None and abs(line_sum - subtotal) > max(tol, 0.001 * abs(subtotal)):
        issues.append(_issue("line_items", f"sum {subtotal:.2f}", f"{line_sum:.2f}", "sum(qty*unit_price) != subtotal"))
    signs = {amount > 0 for amount in (subtotal, total) if amount != 0}
    if len(signs) > 1:
        issues.append(_issue("subtotal/total", "same sign", f"{subtotal}/{total}", "mixed signs"))
    if items and subtotal != 0:
        qty_negative = [float(item.get("qty", 0)) < 0 for item in items if isinstance(item, dict) and isinstance(item.get("qty"), (int, float))]
        if qty_negative and (all(qty_negative) != (subtotal < 0)):
            issues.append(_issue("line_items.qty", "sign matches subtotal", f"subtotal={subtotal}", "credit-note sign disagreement"))
    invoice_date = _iso(pred.get("invoice_date"))
    due_date = _iso(pred.get("due_date")) if pred.get("due_date") else None
    if _iso(pred.get("invoice_date")) is None:
        issues.append(_issue("invoice_date", "YYYY-MM-DD", pred.get("invoice_date"), "not a valid ISO date"))
    if pred.get("due_date") and due_date is None:
        issues.append(_issue("due_date", "YYYY-MM-DD or null", pred.get("due_date"), "not a valid ISO date"))
    if invoice_date and due_date and due_date < invoice_date:
        issues.append(_issue("due_date", ">= invoice_date", pred["due_date"], "due date before invoice date"))
    return issues


def all_issues(pred: dict, schema: dict | None = None) -> list[Issue]:
    schema_issues = validate(pred, schema) if schema else []
    return schema_issues + semantic_issues(pred)


# ---------------------------------------------------------------- 7. SCHEMA AUDIT
UNSUPPORTED = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
               "maxItems", "uniqueItems", "oneOf", "not", "patternProperties", "if", "then", "else"}


def audit(schema: dict) -> dict:
    problems: list[str] = []
    stats = {"objects": 0, "optional": 0, "unions": 0}

    def walk(node, path="$"):
        if not isinstance(node, dict):
            return
        if node.get("type") == "object" or "properties" in node:
            stats["objects"] += 1
            if node.get("additionalProperties") is not False:
                problems.append(f"{path}: object without additionalProperties:false")
            required = set(node.get("required", []))
            for property_name, property_schema in (node.get("properties") or {}).items():
                if property_name not in required:
                    stats["optional"] += 1
                walk(property_schema, f"{path}.{property_name}")
        for keyword in node:
            if keyword in UNSUPPORTED:
                problems.append(f"{path}: unsupported keyword '{keyword}'")
        if isinstance(node.get("type"), list):
            problems.append(f"{path}: type array {node['type']} - use anyOf [{{type}}, {{type:null}}]")
        if "$ref" in node and not str(node["$ref"]).startswith("#"):
            problems.append(f"{path}: external $ref")
        if "minItems" in node and node["minItems"] not in (0, 1):
            problems.append(f"{path}: minItems must be 0 or 1")
        if "anyOf" in node:
            stats["unions"] += 1
            for index, branch in enumerate(node["anyOf"]):
                walk(branch, f"{path}.anyOf[{index}]")
        if "items" in node:
            walk(node["items"], f"{path}[]")

    walk(schema)
    if stats["optional"] > 24:
        problems.append(f"{stats['optional']} optional parameters > 24")
    if stats["unions"] > 16:
        problems.append(f"{stats['unions']} union-typed parameters > 16")
    return {"ok": not problems, "problems": problems, **stats}


# ---------------------------------------------------------------- 8. REPORT
SHORT = {"invoice_number": "inv#", "vendor": "vendr", "invoice_date": "date", "due_date": "due", "currency": "ccy",
         "subtotal": "sub", "tax": "tax", "total": "total", "line_items": "items", "po_number": "po"}


def pct(fraction: float) -> str:
    return f"{100 * fraction:5.1f}%"


def delta(value: float, previous: float | None) -> str:
    if previous is None:
        return "    --"
    change = round(100 * (value - previous), 1) + 0.0
    return f"{change:+5.1f}pt"


def _column_width(results: list[RunResult]) -> int:
    return max(11, max(len(result.version) for result in results) + 2)


def print_version_table(results: list[RunResult], title: str = "") -> None:
    if title:
        print(f"\n{title}")
    version_width = max(10, max(len(result.version) for result in results) + 2)
    print(f"{'version':<{version_width}}{'model':<20}{'parse':>7}{'strict':>8}{'accuracy':>10}{'delta':>9}{'nulls':>8}{'leaks':>7}{'$/12docs':>10}")
    previous_accuracy = None
    for result in results:
        summary = result.summary
        print(f"{result.version:<{version_width}}{result.model:<20}{pct(summary.parse_rate):>7}{pct(summary.strict_parse_rate):>8}{pct(summary.accuracy):>10}"
              f"{delta(summary.accuracy, previous_accuracy):>9}{f'{summary.null_hits}/{summary.null_slots}':>8}{len(result.leaks):>7}{result.cost_usd:>10.4f}")
        previous_accuracy = summary.accuracy


def print_field_matrix(results: list[RunResult]) -> None:
    width = _column_width(results)
    print("\nper-field accuracy (rows = fields, columns = versions)")
    print(f"{'field':<16}" + "".join(f"{result.version:>{width}}" for result in results))
    for field_name in FIELDS:
        print(f"{field_name:<16}" + "".join(f"{100 * result.summary.per_field[field_name]:>{width - 1}.0f}%" for result in results))


def print_doc_matrix(results: list[RunResult]) -> None:
    width = _column_width(results)
    print("\nper-document accuracy (a flat average can hide a regression on one document)")
    print(f"{'doc':<6}" + "".join(f"{result.version:>{width}}" for result in results) + f"{'change':>12}")
    for doc_run in results[0].docs:
        accuracies = [result.doc(doc_run.doc_id).score.accuracy for result in results]
        flag = ""
        if len(accuracies) >= 2:
            diff = accuracies[-1] - accuracies[-2]
            flag = "REGRESSED" if diff < -1e-9 else ("improved" if diff > 1e-9 else "same")
        print(f"{doc_run.doc_id:<6}" + "".join(f"{100 * accuracy:>{width - 1}.0f}%" for accuracy in accuracies) + f"{flag:>12}")


def wrong_fields(run: RunResult, doc_id: str) -> list[str]:
    score = run.doc(doc_id).score
    return [field_name for field_name in FIELDS if score.fields[field_name] < 1.0]
