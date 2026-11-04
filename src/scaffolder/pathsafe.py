"""Path and filesystem safety (architecture 9.5). Pure checks; nothing here writes."""
import re
import stat
from pathlib import Path, PurePosixPath

WIN_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
BAD_CHARS = re.compile(r'[<>:"|?*/\x00-\x1f\\]')
MAX_COMPONENT = 100
MAX_FULL = 250


def is_link(path: Path) -> bool:
    """Recognize symlinks and Windows reparse points, including junctions."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def linked_ancestor(path: Path) -> Path | None:
    """Find a link in a destination path before following it."""
    return next((p for p in (path, *path.parents) if is_link(p)), None)


def check_component(name):
    """Problems with one file or folder name."""
    p = []
    if not name or name in (".", ".."):
        return [f"'{name}' is not a usable name"]
    if BAD_CHARS.search(name):
        p.append(f"'{name}' contains characters that are invalid on Windows")
    if name != name.rstrip(" ."):
        p.append(f"'{name}' ends with a space or dot")
    if name.split(".")[0].upper() in WIN_RESERVED:
        p.append(f"'{name}' is a reserved Windows name")
    if len(name) > MAX_COMPONENT:
        p.append(f"'{name[:20]}...' is too long")
    return p


def check_rel_path(path):
    """Problems with a project-relative path coming from a layer."""
    if not isinstance(path, str) or not path.strip():
        return ["empty path"]
    if "\\" in path:
        return [f"'{path}' uses backslashes; use forward slashes"]
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path) or path.startswith("~"):
        return [f"'{path}' is absolute; layers may only use paths inside the project"]
    parts = PurePosixPath(path).parts
    if ".." in parts:
        return [f"'{path}' tries to leave the project folder"]
    out = []
    for part in parts:
        out += check_component(part)
    return out


def casefold_collisions(paths):
    """Paths that differ only by letter case (collide on Windows and macOS)."""
    seen, out = {}, []
    for p in paths:
        key = p.casefold()
        if key in seen and seen[key] != p:
            out.append(f"'{seen[key]}' and '{p}' differ only by letter case")
        seen.setdefault(key, p)
    return out


SYSTEM_DIRS = {"/", "/bin", "/boot", "/dev", "/etc", "/lib", "/proc", "/sbin", "/sys", "/usr", "/var", "/root"}


def check_target_root(root):
    """Problems with where the project folder would be created. Returns (errors, warnings)."""
    errors, warnings = [], []
    root = Path(root)
    parent = root.parent
    for cand in (root, parent):
        s = str(cand).replace("\\", "/").rstrip("/") or "/"
        if s in SYSTEM_DIRS or re.match(r"(?i)^[a-z]:/(windows|program files)", s):
            errors.append(f"{cand} is a system folder; choose another location")
    link = linked_ancestor(root)
    if link is not None:
        errors.append(f"{link} is a link or reparse point; choose a real folder")
    if len(str(root)) > MAX_FULL - 60:
        errors.append("the project location path is too long; choose a shorter one")
    for anc in (parent, *parent.parents):
        if (anc / ".project.json").exists():
            warnings.append(f"{anc} already looks like a scaffolded project; this would nest inside it")
            break
    return errors, warnings
