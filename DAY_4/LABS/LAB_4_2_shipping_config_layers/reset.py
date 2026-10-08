"""Install or remove the user-level CLAUDE.md for Lab 4.2.

  python reset.py --user install   copy STARTER/home_claude/CLAUDE.md to ~/.claude/CLAUDE.md
  python reset.py --user remove    take it out again (your own file is restored from a backup)
"""
import argparse
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
USER_FILE = pathlib.Path.home() / ".claude" / "CLAUDE.md"
BACKUP = pathlib.Path.home() / ".claude" / "CLAUDE.md.lab42.bak"

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--user", choices=["install", "remove"], required=True)
action = parser.parse_args().user

USER_FILE.parent.mkdir(parents=True, exist_ok=True)
if action == "install":
    if USER_FILE.exists() and not BACKUP.exists():
        shutil.copyfile(USER_FILE, BACKUP)
    shutil.copyfile(HERE / "STARTER" / "home_claude" / "CLAUDE.md", USER_FILE)
    print("installed %s (your old file, if any, is saved as %s)" % (USER_FILE, BACKUP.name))
elif BACKUP.exists():
    shutil.move(str(BACKUP), str(USER_FILE))
    print("restored your original %s" % USER_FILE)
elif USER_FILE.exists():
    USER_FILE.unlink()
    print("removed %s" % USER_FILE)
