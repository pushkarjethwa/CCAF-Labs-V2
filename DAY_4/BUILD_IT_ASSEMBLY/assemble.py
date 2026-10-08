"""Assemble the Brew & Bean working repository, one part at a time.

    python assemble.py --list
    python assemble.py --part 0                 create work/brewbean-rewards from repo_base, git init, first commit
    python assemble.py --part 2                 overlay PART_02_*/files onto the repo
    python assemble.py --part 3 --step b        apply the second stage of a part (Part 3 hook)
    python assemble.py --upto 4                 apply parts 0..4 in order
    python assemble.py --part 3 --commit        overlay, then commit the change on the current branch

Parts are found by the folder pattern PART_[0-9][0-9]_*. Files outside what a part ships are never touched.
"""
import argparse
import glob
import os
import shutil
import stat
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPO = os.path.join(HERE, "work", "brewbean-rewards")


def discover_parts(root=HERE):
    """Return {number: folder_path} for every PART_NN_* folder."""
    parts = {}
    for folder in sorted(glob.glob(os.path.join(root, "PART_[0-9][0-9]_*"))):
        if os.path.isdir(folder):
            parts[int(os.path.basename(folder)[5:7])] = folder
    return parts


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", repo] + list(args), check=check,
                          capture_output=True, text=True)


def _force_remove(func, path, _info):
    os.chmod(path, stat.S_IWRITE)
    func(path)


def copy_tree(src, dst):
    """Copy every file under src into dst. Return (files_copied, files_replaced)."""
    copied = replaced = 0
    for folder, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        target_dir = os.path.join(dst, os.path.relpath(folder, src))
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            if name.endswith(".pyc"):
                continue
            target = os.path.join(target_dir, name)
            replaced += os.path.exists(target)
            shutil.copy2(os.path.join(folder, name), target)
            copied += 1
    return copied, replaced


def create_repo(repo, force=False):
    if os.path.exists(repo):
        if not force:
            print("PART 0: %s already exists. Use --force to recreate it." % repo)
            return False
        shutil.rmtree(repo, onerror=_force_remove)
    count, _ = copy_tree(os.path.join(HERE, "repo_base"), repo)
    git(repo, "init", "-q")
    git(repo, "symbolic-ref", "HEAD", "refs/heads/main")
    for key, value in (("user.name", "Brew Bean Student"), ("user.email", "student@example.com")):
        if not git(repo, "config", key, check=False).stdout.strip():
            git(repo, "config", key, value)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "Start brewbean-rewards")
    print("PART 0: copied %d files from repo_base to %s, ran git init, first commit on branch main." % (count, repo))
    return True


def overlay(number, folder, repo, commit=False, step=None):
    """Overlay PART_N/files, or PART_N/files_step_<step> when a part ships a second stage."""
    sub = "files" if not step else "files_step_" + step
    files = os.path.join(folder, sub)
    name = os.path.basename(folder)
    if not os.path.isdir(files):
        if step is None or "--upto" not in sys.argv:
            print("PART %d: %s ships no %s, nothing to copy." % (number, name, sub))
        return
    if not os.path.isdir(repo):
        sys.exit("The repo %s does not exist. Run: python assemble.py --part 0" % repo)
    count, replaced = copy_tree(files, repo)
    print("PART %d: copied %d files from %s/%s into %s (%d replaced)." % (number, count, name, sub, repo, replaced))
    if commit:
        git(repo, "add", "-A")
        if git(repo, "diff", "--cached", "--quiet", check=False).returncode:
            git(repo, "commit", "-q", "-m", "Add " + name + ("" if not step else " step " + step))
            print("PART %d: committed." % number)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--part", type=int, help="apply one part")
    parser.add_argument("--upto", type=int, help="apply parts 0..N in order")
    parser.add_argument("--list", action="store_true", help="show the parts")
    parser.add_argument("--step", help="with --part: apply a second stage, for example --part 3 --step b")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="working repo (default work/brewbean-rewards)")
    parser.add_argument("--force", action="store_true", help="with part 0: recreate an existing repo")
    parser.add_argument("--commit", action="store_true", help="commit after each overlay (parts 1 and up)")
    args = parser.parse_args(argv)
    parts = discover_parts()
    repo = os.path.abspath(args.repo)
    if args.list:
        for number, folder in parts.items():
            print("%02d  %s%s" % (number, os.path.basename(folder),
                                  "" if os.path.isdir(os.path.join(folder, "files")) else "  (no files)"))
        return 0
    if args.part is None and args.upto is None:
        parser.error("give --part N, --upto N or --list")
    wanted = [args.part] if args.part is not None else [n for n in parts if n <= args.upto]
    for number in wanted:
        if number not in parts:
            sys.exit("PART %d does not exist yet. Parts found: %s" % (number, sorted(parts)))
        if number == 0:
            if args.part is None and os.path.isdir(repo):
                print("PART 0: repo already exists, skipped.")
            elif not create_repo(repo, args.force):
                return 1
        else:
            overlay(number, parts[number], repo, args.commit, args.step if args.part is not None else None)
            if args.part is None:
                overlay(number, parts[number], repo, args.commit, "b")
    return 0


if __name__ == "__main__":
    sys.exit(main())
