"""Part 6 check: the scorecard files are present."""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.parse_args()
    results = []

    def check(name, ok):
        results.append(bool(ok))
        print("[%s] %s" % ("PASS" if ok else "FAIL", name))

    for name in ("GUIDE.md", "QUIZ.md"):
        check("PART_06_scorecard/%s present" % name, os.path.isfile(os.path.join(HERE, name)))
    quiz = os.path.join(HERE, "QUIZ.md")
    text = open(quiz, encoding="utf-8").read() if os.path.isfile(quiz) else ""
    check("quiz has 10 questions", len(re.findall(r"^### Question \d+", text, re.M)) == 10)
    check("quiz has an answer key with 10 answers", len(re.findall(r"^\d+\. [A-D]\b", text.split("## Answer key")[-1], re.M)) == 10)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
