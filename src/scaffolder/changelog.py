"""Preview changelog initialization and releases without inventing change history."""
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .layers import TEMPLATES_DIR
from .pathsafe import linked_ancestor

SEMVER = re.compile(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
)
SECTION = re.compile(r"^## [^\r\n]+", re.MULTILINE)


class ChangelogError(ValueError):
    """The changelog cannot safely be updated."""


@dataclass
class ChangelogPlan:
    path: Path
    before: bytes | None
    after: bytes


def _version(value: str) -> tuple:
    match = SEMVER.fullmatch(value)
    if not match:
        raise ChangelogError("Use a Semantic Version such as 1.2.3 or 1.2.3-rc.1 (without v).")
    major, minor, patch, prerelease, _ = match.groups()
    identifiers = prerelease.split(".") if prerelease else []
    if any(part.isdigit() and len(part) > 1 and part.startswith("0") for part in identifiers):
        raise ChangelogError("Numeric prerelease identifiers cannot have leading zeroes.")
    # Numeric prerelease identifiers precede text; a final release follows prereleases.
    pre = tuple((0, int(part)) if part.isdigit() else (1, part) for part in identifiers)
    return (int(major), int(minor), int(patch), not bool(prerelease), pre)


def _read(path: Path) -> bytes | None:
    if linked_ancestor(path) or not path.parent.is_dir():
        raise ChangelogError("Choose an existing real project directory, without linked paths.")
    if path.exists() and not path.is_file():
        raise ChangelogError("CHANGELOG.md exists but is not a file.")
    return path.read_bytes() if path.exists() else None


def plan(root: str | Path, version: str | None = None,
         release_date: str | None = None) -> ChangelogPlan:
    """Create a read-only plan for one root CHANGELOG.md; retain historical bytes."""
    path = Path(root).expanduser().absolute() / "CHANGELOG.md"
    before = _read(path)
    if release_date is not None and version is None:
        raise ChangelogError("--release-date requires --release.")
    if version is None:
        after = before if before is not None else (TEMPLATES_DIR / "v2/changelog.md").read_bytes()
        return ChangelogPlan(path, before, after)
    key = _version(version)
    stamp = release_date if release_date is not None else date.today().isoformat()
    try:
        if date.fromisoformat(stamp).isoformat() != stamp:
            raise ValueError
    except ValueError as exc:
        raise ChangelogError("Use a valid release date in YYYY-MM-DD format.") from exc
    if before is None:
        raise ChangelogError("Create CHANGELOG.md and add Unreleased changes before making a release.")
    text = before.decode("utf-8")
    sections = list(SECTION.finditer(text))
    if (not sections or sections[0].group() != "## [Unreleased]"
            or sum(section.group() == "## [Unreleased]" for section in sections) != 1):
        raise ChangelogError("Expected exactly one ## [Unreleased] as the first version section.")
    for section in sections[1:]:
        heading = re.fullmatch(r"## \[([^\]]+)\] - [0-9]{4}-[0-9]{2}-[0-9]{2}", section.group())
        if not heading:
            raise ChangelogError("Existing release headings must use ## [VERSION] - YYYY-MM-DD.")
        old_version = heading.group(1)
        if key <= _version(old_version):
            raise ChangelogError(f"Release must be newer than existing version {old_version}; duplicates are refused.")
    start = sections[0].end()
    end = sections[1].start() if len(sections) > 1 else len(text)
    body = text[start:end]
    # Reference definitions at the bottom belong to the document, not the release.
    refs = re.search(r"^\[[^\]\r\n]+\]:[ \t]+\S", body, re.MULTILINE)
    if refs:
        end = start + refs.start()
        body = text[start:end]
    if not re.search(r"^(?:- |\* )\S", body, re.MULTILINE):
        raise ChangelogError("Unreleased has no change entries; nothing to release.")
    newline = "\r\n" if "\r\n" in text else "\n"
    after = (text[:start] + newline * 2 + f"## [{version}] - {stamp}" + newline * 2
             + body.strip("\r\n") + newline * 2 + text[end:])
    return ChangelogPlan(path, before, after.encode("utf-8"))


def preview(result: ChangelogPlan) -> None:
    """Show the complete proposed changelog before confirmation."""
    action = "Create" if result.before is None else "Update"
    if result.before == result.after:
        print(f"Already exists; no changes: {result.path}")
        return
    print(f"{action}: {result.path}\n")
    print(result.after.decode("utf-8"))


def apply(result: ChangelogPlan) -> None:
    """Recheck the preview before writing; never overwrite a newly created file."""
    if _read(result.path) != result.before:
        raise ChangelogError("CHANGELOG.md changed since preview; run the command again.")
    if result.before == result.after:
        return
    mode = "xb" if result.before is None else "wb"
    with result.path.open(mode) as stream:
        stream.write(result.after)
