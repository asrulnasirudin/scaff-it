"""The only module that runs Git. Allowed: init, add, commit, rev-parse, config, symbolic-ref.
Never: push, remote changes, branch/worktree creation, history rewriting, force, deletion.
"""
import os
import shutil
import subprocess
from pathlib import Path

ALLOWED = {"init", "add", "commit", "rev-parse", "config", "symbolic-ref"}


def available():
    return shutil.which("git") is not None


def _git(cwd, *args):
    if args[0] not in ALLOWED:
        raise ValueError(f"git {args[0]} is not allowed in this tool")
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def parent_warnings(root):
    """Read-only: warn when the new project would sit inside another Git repository."""
    if not available():
        return []
    anc = Path(root).parent
    while not anc.exists() and anc != anc.parent:
        anc = anc.parent
    r = _git(anc, "rev-parse", "--show-toplevel")
    if r.returncode == 0 and r.stdout.strip():
        return [f"The location is inside another Git repository ({r.stdout.strip()}); "
                "this project would become a separate nested repository."]
    return []


def init(root, branch="main"):
    """Create a local repository on the given branch. Returns (ok, message)."""
    if not available():
        return False, "Git is not installed; skipped `git init`."
    r = _git(root, "init", "-b", branch)
    if r.returncode != 0:  # older Git without -b
        r = _git(root, "init")
        if r.returncode != 0:
            return False, f"`git init` failed: {r.stderr.strip()}"
        _git(root, "symbolic-ref", "HEAD", f"refs/heads/{branch}")
    return True, f"Git repository created on branch '{branch}'. No commit was made."


def has_identity(root):
    if os.environ.get("GIT_AUTHOR_NAME") and os.environ.get("GIT_AUTHOR_EMAIL"):
        return True
    name = _git(root, "config", "user.name").stdout.strip()
    email = _git(root, "config", "user.email").stdout.strip()
    return bool(name and email)


def first_commit(root, message="Scaffold project structure"):
    """Stage and commit. Uses your own Git identity; never invents one. Returns (ok, message)."""
    if not has_identity(root):
        return False, ("First commit skipped: Git has no user.name / user.email. "
                       "Set them, then run `git add -A` and `git commit` yourself.")
    r = _git(root, "add", "-A")
    if r.returncode != 0:
        return False, f"`git add` failed: {r.stderr.strip()}"
    r = _git(root, "commit", "-m", message)
    if r.returncode != 0:
        return False, f"`git commit` failed: {r.stderr.strip() or r.stdout.strip()}"
    return True, "First commit created."
