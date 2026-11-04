"""Add missing scaffold files to an existing project without replacing its files."""
import copy
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

from . import pathsafe
from .apply import ApplyError, Journal, sha
from .layers import Layer
from .resolve import Resolved


@dataclass
class AdditionPlan:
    resolved: Resolved
    files: dict
    dirs: list
    preserved: list
    observed: dict


def existing_catalog(catalog: dict) -> dict:
    """Expose the existing state only to the explicit adoption workflow."""
    result = dict(catalog)
    result.pop("state:new")
    result["state:existing"] = Layer("state", "existing", "Existing project", "1", {
        "description": "Add missing scaffold files while preserving existing files.", "default": True})
    return result


def _inspect(root: Path, relative: str) -> tuple:
    """Inspect only a planned path and its ancestors; never read existing file contents."""
    if pathsafe.linked_ancestor(root) is not None:
        raise ValueError("The selected folder has a linked path or reparse point.")
    current = root
    for part in PurePosixPath(relative).parts:
        # Match case explicitly, including on case-sensitive test/development hosts.
        matches = [p for p in current.iterdir() if p.name.casefold() == part.casefold()]
        if len(matches) > 1 or (matches and matches[0].name != part):
            raise ValueError(f"{relative}: existing path differs by letter case; review it manually.")
        current = current / part
        if pathsafe.is_link(current):
            raise ValueError(f"{relative}: link or reparse point in scaffold destination.")
        if not current.exists():
            return ("missing",)
        if current != root / relative and not current.is_dir():
            raise ValueError(f"{relative}: an existing file blocks a required folder.")
    return ("directory",) if current.is_dir() else ("file",)


def plan(resolved: Resolved) -> AdditionPlan:
    """Classify additions and preserve existing files, including existing descriptors."""
    root = resolved.root
    if not root.is_dir():
        raise ValueError("Choose an existing project folder.")
    errors, _ = pathsafe.check_target_root(root)
    if errors:
        raise ValueError("; ".join(errors))
    observed, files, preserved = {}, {}, []
    candidates = dict(resolved.files)
    # Never claim an existing application has not been implemented or tested.
    if ".agent/CHECKPOINT.md" in candidates:
        candidates[".agent/CHECKPOINT.md"] = (
            "# Checkpoint\n\nExisting project scaffold setup.\n\n"
            "- Missing scaffold files were added; existing files were preserved.\n"
            "- Application implementation, tests, Git state, and requirements have not been assessed.\n"
            "- Review existing code, documentation, folder roles, and ignore rules before development.\n")
    if ".agent/PLANS.md" in candidates:
        candidates[".agent/PLANS.md"] = (
            "# Plans\n\n1. [ ] Review existing code, requirements, folder layout, and tests.\n"
            "2. [ ] Reconcile scaffold guidance with existing project conventions and ignore rules.\n"
            "3. [ ] Record verified progress and agree on the next change.\n")
    if "AGENTS.md" in candidates:
        candidates["AGENTS.md"] = candidates["AGENTS.md"].replace(
            "Git is not used for this project.", "Existing Git configuration and history are preserved by setup.")
        candidates["AGENTS.md"] += (
            "\n## Existing project setup\n"
            "Existing files were preserved. Folder roles and commands above are suggested defaults; "
            "verify them against the actual project. Existing Git configuration and history were kept. "
            "Review ignore rules before adding local working material or secrets. "
            "Application implementation and test status have not been assessed.\n")
    if ".agent/MEMORY.md" in candidates:
        candidates[".agent/MEMORY.md"] = candidates[".agent/MEMORY.md"].replace(
            "Established at setup (confirmed by the owner when the project was created)",
            "Selected during existing-project scaffold setup").replace(
                "Git not used", "existing configuration preserved")
        candidates[".agent/MEMORY.md"] += (
            "\n## Existing project setup\n"
            "Setup answers describe selected scaffolding, not a code audit. "
            "Existing layout, commands, requirements, and Git conventions require review.\n")
    for rel, text in candidates.items():
        pathsafe_errors = pathsafe.check_rel_path(rel)
        if pathsafe_errors:
            raise ValueError("; ".join(pathsafe_errors))
        observed[rel] = state = _inspect(root, rel)
        if state == ("directory",):
            raise ValueError(f"{rel}: a directory blocks a scaffold file.")
        if state == ("file",):
            preserved.append(rel)
        else:
            files[rel] = text
    for rel in resolved.dirs:
        observed[rel] = state = _inspect(root, rel)
        if state == ("file",):
            raise ValueError(f"{rel}: a file blocks a scaffold folder.")
    if ".project.json" in files:
        descriptor = copy.deepcopy(resolved.descriptor)
        descriptor["git"] = {
            "enabled": any((p / ".git").exists() for p in (root, *root.parents)),
            "configuration": "preserved", "commit_policy": "ask"}
        descriptor["scaffold"]["mode"] = "add_missing"
        descriptor["scaffold"]["preserved_files"] = sorted(preserved)
        descriptor["scaffold"]["managed_files"] = [
            {"path": rel, "template": resolved.template_of[rel], "sha256": sha(text)}
            for rel, text in sorted(files.items()) if rel != ".project.json"]
        files[".project.json"] = json.dumps(descriptor, indent=2, ensure_ascii=False) + "\n"
    return AdditionPlan(resolved, files, list(resolved.dirs), sorted(preserved), observed)


def preview(additions: AdditionPlan) -> None:
    """Show only additions, plus a separate list of preserved scaffold paths."""
    from .apply import preview as scaffold_preview
    scaffold_preview(replace(additions.resolved, files=additions.files), target_state="existing")
    print("\nEXISTING PROJECT: only missing files will be added. Existing files are preserved.")
    for rel in additions.preserved:
        print(f"  Keep existing: {rel}")
    if ".gitignore" in additions.preserved:
        print("Review existing .gitignore rules before adding local material or secrets; it will not be edited.")
    if ".project.json" in additions.preserved:
        print("Existing descriptor is preserved; new files are not added to its historical baseline.")
    print("Existing code and folder layout are not moved. Git history and settings are preserved.")


def apply(additions: AdditionPlan) -> Journal:
    """Recheck destinations and exclusively create missing files; report partial failure."""
    root, journal = additions.resolved.root, Journal()
    try:
        if not root.is_dir():
            raise ValueError("The project folder no longer exists.")
        for rel, expected in additions.observed.items():
            if _inspect(root, rel) != expected:
                raise ValueError(f"{rel}: destination changed after preview; run setup again.")
        for rel in additions.dirs:
            target = root / rel
            missing = [p for p in reversed([target, *target.parents])
                       if root in p.parents and not p.exists()]
            target.mkdir(parents=True, exist_ok=True)
            journal.dirs.extend(p.relative_to(root).as_posix() for p in missing)
        order = sorted(rel for rel in additions.files if rel != ".project.json")
        if ".project.json" in additions.files:
            order.append(".project.json")
        for rel in order:
            if _inspect(root, rel) != ("missing",):
                raise ValueError(f"{rel}: destination changed during setup.")
            target = root / rel
            missing = [p for p in reversed(list(target.parents)) if root in p.parents and not p.exists()]
            target.parent.mkdir(parents=True, exist_ok=True)
            journal.dirs.extend(p.relative_to(root).as_posix() for p in missing)
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                # Record creation before writing so even partial writes are reported.
                journal.files.append((rel, sha(additions.files[rel])))
                stream.write(additions.files[rel])
        for rel, text in additions.files.items():
            if hashlib.sha256((root / rel).read_bytes()).hexdigest() != sha(text):
                raise ValueError(f"{rel}: verification failed after setup.")
    except Exception as exc:
        raise ApplyError(exc, journal) from exc
    return journal
