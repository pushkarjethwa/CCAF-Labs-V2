"""Build a student starter and a trainer solution from ONE annotated source file.

usage: python build_lab.py <lab_source.py> <starter_out.py> <solution_out.py>

Inside the source, a TODO block looks like this:

    # >>>SOLUTION
    real code
    # ---STARTER
    stub code (what the student sees instead)
    # <<<SOLUTION

The solution file keeps the real code; the starter keeps the stub code.
Marker lines are removed from both outputs.
"""
import pathlib
import sys

source, starter_out, solution_out = (pathlib.Path(p) for p in sys.argv[1:4])
starter_lines, solution_lines = [], []
mode = "both"  # both | solution | starter
for line in source.read_text(encoding="utf-8").splitlines():
    marker = line.strip()
    if marker == "# >>>SOLUTION":
        mode = "solution"
    elif marker == "# ---STARTER":
        mode = "starter"
    elif marker == "# <<<SOLUTION":
        mode = "both"
    else:
        if mode in ("both", "starter"):
            starter_lines.append(line)
        if mode in ("both", "solution"):
            solution_lines.append(line)
for out, lines in ((starter_out, starter_lines), (solution_out, solution_lines)):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
