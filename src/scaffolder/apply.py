"""Preview, safe APPLY with a journal, recovery and verification (New state)."""
import hashlib
import sys
from pathlib import PurePosixPath

from .pathsafe import is_link, linked_ancestor
from .theme import paint


class ApplyError(Exception):
    def __init__(self, cause, journal):
        self.cause, self.journal = cause, journal
        super().__init__(str(cause))


class Journal:
    """What this run created, so a failed run can report exactly what is on disk."""

    def __init__(self):
        self.root_created = False
        self.dirs = []      # directories this run created, in order
        self.files = []     # (relative path, sha256) this run wrote
        self.skipped = []   # identical files that already existed

    @property
    def count(self):
        return len(self.dirs) + len(self.files) + (1 if self.root_created else 0)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Preview
# --------------------------------------------------------------------------
def render_tree(res):
    """ASCII tree of everything that would be created; '~' marks folders tooling creates later."""
    tree = {}
    for p in list(res.files) + [d + "/" for d in res.dirs]:
        node = tree
        for part in PurePosixPath(p).parts:
            node = node.setdefault(part, {})
    later = [s["path"] for s in res.cfg["roles"].values() if s and s["origin"] == "tool_created"]
    for p in later:
        node = tree
        for part in PurePosixPath(p).parts:
            node = node.setdefault(part, {})
        node["\x00later"] = {}
    lines = [res.root.name + "/"]

    dirset = set(res.dirs)

    def walk(node, prefix, path=""):
        items = sorted((k for k in node if k != "\x00later"), key=lambda k: (not node[k], k.lower()))
        for i, k in enumerate(items):
            last = i == len(items) - 1
            is_later = "\x00later" in node[k]
            full = f"{path}{k}"
            label = f"~ {k}/  (created later by build tools)" if is_later else (k + "/" if node[k] or full in dirset else k)
            lines.append(f"{prefix}{'`-- ' if last else '|-- '}{label}")
            if node[k] and not is_later:
                walk(node[k], prefix + ("    " if last else "|   "), full + "/")

    walk(tree, "")
    return "\n".join(lines)


def preview(res, target_state="empty", out=None):
    out = out or sys.stdout
    c, ch = res.cfg, res.choices
    p = lambda *a: print(*a, file=out)
    p(f"\nPROJECT:   {ch.name}" + (f" - {ch.description.strip()}" if ch.description.strip() else ""))
    p(f"Location:  {res.root}")
    for label, kind in (("Category", "category"), ("Platform", "platform"), ("Host", "target"),
                        ("Stack", "stack"), ("AI", "ai"), ("Distribution", "distribution")):
        names = [l.label for l in res.layers if l.kind == kind and not l.hidden]
        p(f"{label + ':':<11}" + (", ".join(names) if names else ("undecided" if kind == "stack" else "none")))
    feats = [l.label for l in res.layers if l.kind == "feature"]
    p("Extras:    " + (", ".join(feats) if feats else "none"))
    git_status = (f"initialise on main, workflow {ch.git_workflow}, first commit "
                         + ("YES (after the safety check)" if ch.first_commit else "no (you decide later)")
                         if ch.git else "not used")
    if target_state == "existing":
        git_status = "existing configuration and history preserved"
    p("Git:        " + git_status)
    p("Layers:    " + ", ".join(l.ref for l in res.layers if l.ref != "base:base"))
    p(paint("\nPROPOSED STRUCTURE\n", out=out))
    p(render_tree(res))
    p(f"\n{len(res.files)} files will be created.")
    if target_state == "resumable":
        p("Note: the folder holds an earlier, interrupted run. Identical files are kept; missing ones are added.")
    p(paint("\nSECURITY", "panel", out=out))
    p("  - Never committed (secrets): " + ", ".join(c["secret"]))
    local = [x + "/" for x in c["local_paths"]] + c["local_only"]
    p("  - Local-only (git-ignored): " + (", ".join(local) if local else "none"))
    p("  - Flagged for review, not ignored: " + ", ".join(c["watch"]))
    p(f"  - Large-file warning above {c['large_file_warn_mb']} MB")
    if c["toolchain"]:
        p("Toolchain requirements (profile defaults; edit .project.json to change; nothing is installed): "
          + ", ".join(f"{k} {v}" for k, v in c["toolchain"].items()))
    for w in res.warnings:
        p(f"{w if w.startswith('Note:') else 'Warning: ' + w}")


MENU = "\n[C]reate  [M]odify  [B]ack  [X] Cancel: "


def menu(out=None):
    """Returns 'create', 'modify', 'back' or 'cancel'. No input available means cancel."""
    print("\nC Create: write the folders and files shown in the preview.\n"
          "M Modify: choose an answer to change, then review the preview again.\n"
          "B Back: revisit the last setup question.\n"
          "X Cancel: exit without creating the project. Enter also cancels.", file=out or sys.stdout)
    while True:
        try:
            ans = input(MENU).strip().lower()
        except EOFError:
            return "cancel"
        if ans in ("c", "create", "y", "yes"):
            return "create"
        if ans in ("m", "modify"):
            return "modify"
        if ans in ("b", "back"):
            return "back"
        if ans in ("x", "cancel", "n", "no", "q", ""):
            return "cancel"
        print("Please type C, M, B or X.", file=out or sys.stdout)


# --------------------------------------------------------------------------
# Target folder inspection (read-only) and drift detection
# --------------------------------------------------------------------------
def classify_target(res):
    """('empty' | 'resumable' | 'conflict', details). Never writes."""
    root = res.root
    link = linked_ancestor(root)
    if link is not None:
        return "conflict", [f"{link} is a link or reparse point."]
    if not root.exists():
        return "empty", []
    if not root.is_dir():
        return "conflict", [f"{root} exists and is not a folder."]
    existing, pending = [], [root]
    while pending:
        for p in pending.pop().iterdir():
            if is_link(p):
                return "conflict", [f"{p.relative_to(root)} is a link or reparse point."]
            if p.is_dir():
                pending.append(p)
            else:
                existing.append(p)
    if not existing:
        return "empty", []
    if (root / ".project.json").exists():
        return "conflict", ["This folder is already a scaffolded project. Use --scaffold-existing PROJECT "
                            "to add missing scaffold files while preserving existing content."]
    problems = []
    for p in existing:
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            problems.append(f"{rel} is a link")
        elif rel not in res.files:
            problems.append(f"{rel} is not part of this project")
        elif p.read_text(encoding="utf-8", errors="replace") != res.files[rel]:
            problems.append(f"{rel} exists with different content")
    return ("conflict", problems) if problems else ("resumable", [])


# --------------------------------------------------------------------------
# Apply, recovery, verification
# --------------------------------------------------------------------------
def _write_file(path, text):
    # Exclusive creation prevents a newly appeared file from being overwritten.
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def apply(res, _write=_write_file):
    """Create the project. Existing identical files are skipped; .project.json is written last.
    Raises ApplyError (carrying the journal) if anything fails part-way."""
    state, problems = classify_target(res)   # drift re-check right before writing
    if state == "conflict":
        raise ApplyError(RuntimeError("; ".join(problems)), Journal())
    root, j = res.root, Journal()
    try:
        if not root.exists():
            root.mkdir(parents=True)
            j.root_created = True
        for d in res.dirs:
            target = root / d
            if linked_ancestor(target) is not None:
                raise ValueError(f"{d}: destination became a link or reparse point")
            missing = [x for x in reversed([target, *target.parents]) if x != root and root in x.parents and not x.exists()]
            target.mkdir(parents=True, exist_ok=True)
            j.dirs += [m.relative_to(root).as_posix() for m in missing]
        order = [p for p in res.files if p != ".project.json"] + [".project.json"]
        for rel in order:
            target = root / rel
            if linked_ancestor(target) is not None:
                raise ValueError(f"{rel}: destination became a link or reparse point")
            if target.exists():
                if not target.is_file() or target.read_text(encoding="utf-8") != res.files[rel]:
                    raise ValueError(f"{rel}: destination changed during creation")
                j.skipped.append(rel)
                continue
            missing = [x for x in reversed(list(target.parents)) if x != root and root in x.parents and not x.exists()]
            target.parent.mkdir(parents=True, exist_ok=True)
            j.dirs += [m.relative_to(root).as_posix() for m in missing]
            _write(target, res.files[rel])
            j.files.append((rel, sha(res.files[rel])))
    except Exception as e:  # noqa: BLE001 - report, never hide
        raise ApplyError(e, j)
    return j


def rollback(res, j):
    """Opt-in: remove only what this run created and only if still unchanged. Returns (removed, kept)."""
    root, removed, kept = res.root, [], []
    for rel, digest in reversed(j.files):
        p = root / rel
        if linked_ancestor(p) is not None:
            kept.append(rel)
            continue
        if not p.exists():
            continue
        if sha(p.read_text(encoding="utf-8", errors="replace")) == digest:
            p.unlink()
            removed.append(rel)
        else:
            kept.append(rel)
    for rel in reversed(j.dirs):
        p = root / rel
        if linked_ancestor(p) is not None:
            kept.append(rel + "/")
            continue
        if p.is_dir() and not any(p.iterdir()):
            p.rmdir()
            removed.append(rel + "/")
    if j.root_created and linked_ancestor(root) is None and root.is_dir() and not any(root.iterdir()):
        root.rmdir()
        removed.append(root.name + "/")
    return removed, kept


def verify(res):
    """Problems found after creation (empty list = project matches the plan exactly)."""
    problems = []
    for rel, text in res.files.items():
        p = res.root / rel
        if not p.is_file():
            problems.append(f"missing: {rel}")
        elif p.read_text(encoding="utf-8", errors="replace") != text:
            problems.append(f"differs from plan: {rel}")
    for d in res.dirs:
        if not (res.root / d).is_dir():
            problems.append(f"missing folder: {d}/")
    return problems
