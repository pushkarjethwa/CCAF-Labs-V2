"""Demo 5G - Loads the author-written fixtures in data/. Plain Python: no SDK, no model, no network."""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"


def load(name):
    """Read data/<name>.json. The `_note` key (a label that says the file is a fixture) is dropped."""
    data = json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))
    data.pop("_note", None)
    return data
