"""vault.py - a versioned, hash-locked prompt vault and a regression gate. GIVEN: read it, do not edit.

Rules the vault enforces:
  1. A prompt is a FILE with a version number, a parent and a change note (prompts/vault.json).
  2. The file's sha256 is recorded in prompts/vault.lock.json. Editing a released file without bumping the version makes
     verify() fail: a silent prompt edit is a production change with no review and no regression run.
  3. Exactly one version has status "production".
The gate: a candidate prompt may replace the baseline only if it does not get worse (overall, per field, per document,
parse rate, null handling, and example leaks). An average alone is not enough: an average hid a real regression at v4.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from evalkit import FIELDS, PROMPTS_DIR, PromptVersion, load_prompt_file, load_schema, load_vault_meta, load_versions

LOCK_NAME = "vault.lock.json"


@dataclass
class VerifyReport:
    ok: bool
    problems: list[str]


class Vault:
    def __init__(self, prompts_dir: Path | None = None):
        self.dir = Path(prompts_dir) if prompts_dir else PROMPTS_DIR
        self.meta = load_vault_meta(self.dir)
        self.versions = load_versions(self.dir, include_ablations=True)

    # ------------------------------------------------------------ lookup
    def get(self, version: str) -> PromptVersion:
        try:
            return self.versions[version]
        except KeyError:
            raise KeyError(f"unknown prompt version {version!r}; known: {', '.join(self.versions)}") from None

    def production(self) -> PromptVersion:
        production = [prompt for prompt in self.versions.values() if prompt.status == "production"]
        if len(production) != 1:
            raise RuntimeError(f"vault must have exactly one production version, found {len(production)}")
        return production[0]

    def candidate_from_file(self, path: Path, *, like: str | None = None) -> PromptVersion:
        """Load a not-yet-registered prompt file. It inherits the schema of `like` (default: production)."""
        base = self.get(like) if like else self.production()
        return load_prompt_file(Path(path), Path(path).stem, base.schema, parent=base.version, status="candidate",
                                change=f"candidate loaded from {Path(path).name}")

    def lineage(self, version: str) -> list[str]:
        chain, current = [], version
        while current:
            chain.append(current)
            current = self.get(current).parent
        return chain[::-1]

    # ------------------------------------------------------------ integrity
    def lock(self) -> Path:
        hashes = {version: prompt.sha256 for version, prompt in self.versions.items()}
        hashes["schema_invoice.json"] = hashlib.sha256((self.dir / self.meta["schema"]).read_bytes()).hexdigest()
        lock_path = self.dir / LOCK_NAME
        lock_path.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return lock_path

    def verify(self) -> VerifyReport:
        problems: list[str] = []
        lock_path = self.dir / LOCK_NAME
        if not lock_path.exists():
            return VerifyReport(False, [f"{LOCK_NAME} missing - run `cli.py lock` after review"])
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        for version, prompt in self.versions.items():
            if version not in lock:
                problems.append(f"{version}: not in lock file (unreviewed new version)")
            elif lock[version] != prompt.sha256:
                problems.append(f"{version}: file changed since lock (edit a released prompt = new version number)")
        schema_hash = hashlib.sha256((self.dir / self.meta["schema"]).read_bytes()).hexdigest()
        if lock.get("schema_invoice.json") != schema_hash:
            problems.append("schema_invoice.json changed since lock")
        for version, prompt in self.versions.items():
            if prompt.parent and prompt.parent not in self.versions:
                problems.append(f"{version}: parent {prompt.parent} does not exist")
        try:
            self.production()
        except RuntimeError as error:
            problems.append(str(error))
        return VerifyReport(not problems, problems)


@dataclass
class GateConfig:
    max_overall_drop: float = 0.01
    max_field_drop: float = 0.05
    max_doc_regressions: int = 1
    max_leaks: int = 0


@dataclass
class GateResult:
    passed: bool
    checks: list[tuple[bool, str]] = field(default_factory=list)

    def print(self) -> None:
        for ok, msg in self.checks:
            print(f"[{'PASS' if ok else 'FAIL'}] {msg}")
        print("GATE: " + ("PASS - candidate may be promoted" if self.passed else "FAIL - candidate rejected"))


def evaluate_gate(base: RunResult, cand: RunResult, cfg: GateConfig | None = None) -> GateResult:
    cfg = cfg or GateConfig()
    baseline, candidate = base.summary, cand.summary
    checks: list[tuple[bool, str]] = []

    drop = baseline.accuracy - candidate.accuracy
    checks.append((drop <= cfg.max_overall_drop + 1e-9,
                   f"overall accuracy {100 * candidate.accuracy:.1f}% vs baseline {100 * baseline.accuracy:.1f}% "
                   f"(change {round(-100 * drop, 1) + 0.0:+.1f}pt, allowed drop {100 * cfg.max_overall_drop:.1f}pt)"))

    worst = max(FIELDS, key=lambda name: baseline.per_field[name] - candidate.per_field[name])
    field_drop = baseline.per_field[worst] - candidate.per_field[worst]
    checks.append((field_drop <= cfg.max_field_drop + 1e-9,
                   f"worst field drop: {worst} {round(-100 * field_drop, 1) + 0.0:+.1f}pt (allowed {100 * cfg.max_field_drop:.1f}pt)"))

    regressed = [doc_run.doc_id for doc_run in base.docs
                 if cand.doc(doc_run.doc_id).score.accuracy < doc_run.score.accuracy - 1e-9]
    checks.append((len(regressed) <= cfg.max_doc_regressions,
                   f"documents that got worse: {len(regressed)} {regressed} (allowed {cfg.max_doc_regressions})"))

    checks.append((candidate.parse_rate >= baseline.parse_rate - 1e-9
                   and candidate.strict_parse_rate >= baseline.strict_parse_rate - 1e-9,
                   f"parse rate loose {100 * candidate.parse_rate:.0f}%/strict {100 * candidate.strict_parse_rate:.0f}% "
                   f"(baseline {100 * baseline.parse_rate:.0f}%/{100 * baseline.strict_parse_rate:.0f}%)"))

    checks.append((candidate.null_handling >= baseline.null_handling - 1e-9,
                   f"null handling {candidate.null_hits}/{candidate.null_slots} (baseline {baseline.null_hits}/{baseline.null_slots})"))

    leaks = [f"{leak.doc_id}.{leak.field}" for leak in cand.leaks]
    checks.append((len(leaks) <= cfg.max_leaks, f"example leaks: {len(leaks)} {leaks} (allowed {cfg.max_leaks})"))

    return GateResult(all(ok for ok, _ in checks), checks)
