"""Rebuild the demo workspace.   python reset.py [--to N] [--final] [--out DIR]

Without options it restores the START state to workspace/bookshop, ready for part 1.
--to N   builds the project as it stands at the START of part N (1 = start, 10 = everything done).
--final  builds the finished project (same as --to 10).
Use it to catch up when you skip a part or when a live run goes somewhere you do not want.
PART folders are copied on top of START_STATE in order; later files win.
  add/       the files you copy in during that part
  reference/ what Claude Code is expected to write in that part (code and tests)
  catch_up/  what a command in that part creates (for example .mcp.json), so a rebuild has it"""
import argparse
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent

# (part number, folder, sub-folders applied once the part is finished)
PARTS = [
    (2, "PART_02_memory", ["add"]),
    (4, "PART_04_slash_command", ["add", "reference"]),
    (5, "PART_05_skill", ["add", "reference"]),
    (6, "PART_06_subagent", ["add"]),
    (7, "PART_07_hook", ["add", "reference"]),
    (8, "PART_08_mcp", ["add", "catch_up"]),
]


def copy_over(src: pathlib.Path, dest: pathlib.Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__"))


def build(dest: pathlib.Path, part: int = 1) -> pathlib.Path:
    """Build the project as it is at the start of `part` (1..10) into dest."""
    shutil.rmtree(dest, ignore_errors=True)
    copy_over(HERE / "START_STATE", dest)
    for number, folder, subs in PARTS:
        if number < part:
            for sub in subs:
                copy_over(HERE / folder / sub, dest)
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--to", type=int, default=1, choices=range(1, 11))
    parser.add_argument("--final", action="store_true")
    parser.add_argument("--out", default=str(HERE / "workspace" / "bookshop"))
    args = parser.parse_args()
    part = 10 if args.final else args.to
    print("Built %s (state at the start of part %d)" % (build(pathlib.Path(args.out), part), part))
