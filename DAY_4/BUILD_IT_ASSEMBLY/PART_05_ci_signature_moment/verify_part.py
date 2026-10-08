"""Part 5 check: the CI review gate files are present and behave as designed (no key, no GitHub)."""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "DATA")
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
FILES = [".ci/findings.schema.json", ".ci/review_prompt.md", ".ci/run_review.py", ".ci/gate.py",
         ".github/workflows/claude-review.yml", "scripts/run_gate_local.py"]
WORKFLOW_PARTS = [
    ("triggers on pull_request", r"^on:\s*\n\s+pull_request:"),
    ("does not use pull_request_target", None),
    ("permissions contents: read", r"contents:\s*read"),
    ("permissions pull-requests: write", r"pull-requests:\s*write"),
    ("checkout with fetch-depth: 0", r"fetch-depth:\s*0"),
    ("installs the Claude Code CLI", r"npm i(nstall)? -g @anthropic-ai/claude-code"),
    ("builds the diff against the base", r"git diff .*origin/.*\.\.\.HEAD"),
    ("runs .ci/run_review.py", r"\.ci/run_review\.py"),
    ("runs .ci/gate.py", r"\.ci/gate\.py"),
    ("key comes from secrets.ANTHROPIC_API_KEY", r"ANTHROPIC_API_KEY:\s*\$\{\{\s*secrets\.ANTHROPIC_API_KEY\s*\}\}"),
    ("posts a PR comment", r"gh pr comment"),
    ("job fails on the gate exit code", r"exit \"\$GATE_CODE\""),
]


def gate(diff, review=None):
    cmd = [sys.executable, os.path.join(REPO, ".ci", "gate.py"), "--diff", diff]
    if review:
        cmd += ["--review", review]
    return subprocess.run(cmd, capture_output=True, text=True, env=ENV).returncode


def main():
    global REPO
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    REPO = os.path.abspath(parser.parse_args().repo)
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    for rel in FILES:
        check("file present: " + rel, os.path.isfile(os.path.join(REPO, rel)))
    path = os.path.join(REPO, ".github", "workflows", "claude-review.yml")
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    try:
        import yaml
        data = yaml.safe_load(text)
        check("workflow is valid YAML with a job", isinstance(data, dict) and bool(data.get("jobs")))
    except ImportError:
        check("workflow has a jobs section (PyYAML not installed, minimal check)", re.search(r"^jobs:\s*$", text, re.M))
    except Exception as err:  # YAML error
        check("workflow is valid YAML: %s" % err, False)
    for name, pattern in WORKFLOW_PARTS:
        if pattern is None:
            check("workflow " + name, "pull_request_target" not in re.sub(r"#.*", "", text))
        else:
            check("workflow " + name, re.search(pattern, text, re.M))
    check("workflow never echoes the key", not re.search(r"echo[^\n]*ANTHROPIC_API_KEY", text))

    # Gate behaviour: recorded reviews give 0 / 1 / 0, plus INVALID and INCONCLUSIVE.
    if os.path.isfile(os.path.join(REPO, ".ci", "gate.py")):
        for name, want in (("good", 0), ("flawed", 1), ("fixed", 0)):
            got = gate(os.path.join(DATA, "pr_%s.patch" % name), os.path.join(DATA, "recorded_review_%s.json" % name))
            check("gate on pr_%s with its recorded review exits %d (got %d)" % (name, want, got), got == want)
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "bad.json")
            open(bad, "w").write("this is prose, not JSON")
            good_diff = os.path.join(DATA, "pr_good.patch")
            check("gate exits 2 (INVALID) on a review that is not JSON", gate(good_diff, bad) == 2)
            check("gate exits 3 (INCONCLUSIVE) when there is no review", gate(good_diff, os.path.join(tmp, "none.json")) == 3)
            check("gate exits 1 (BLOCK) on a flawed diff even with no review", gate(os.path.join(DATA, "pr_flawed.patch")) == 1)

    # The three patches apply to the committed repo (checked on a clean export, so your branch does not matter).
    if os.path.isdir(os.path.join(REPO, ".git")):
        ref = "main" if subprocess.run(["git", "-C", REPO, "rev-parse", "--verify", "-q", "main"],
                                       capture_output=True).returncode == 0 else "HEAD"
        archive = subprocess.run(["git", "-C", REPO, "archive", "--format=tar", ref], capture_output=True)
        with tempfile.TemporaryDirectory() as tmp:
            if archive.returncode == 0:
                with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
                    tar.extractall(tmp)
            for name in ("good", "flawed", "fixed"):
                done = subprocess.run(["git", "apply", "--check", os.path.join(DATA, "pr_%s.patch" % name)],
                                      cwd=tmp, capture_output=True, text=True)
                check("pr_%s.patch applies to %s" % (name, ref), archive.returncode == 0 and done.returncode == 0)
    else:
        check("repo is a git repository", False)
    check("recorded reviews are labelled as recorded samples",
          all(json.load(open(os.path.join(DATA, "recorded_review_%s.json" % n))).get("recorded_sample") is True
              for n in ("good", "flawed", "fixed")))
    return 0 if all(results) else 1


REPO = ""

if __name__ == "__main__":
    sys.exit(main())
