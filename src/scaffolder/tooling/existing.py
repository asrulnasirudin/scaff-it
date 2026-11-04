"""Guided entry point reusing the existing lint setup and consent flow."""
from pathlib import Path

from .. import cli
from ..theme import paint, themed


def browse_folder() -> str | None:
    """Return a selected folder, an empty string on cancel, or None if unavailable."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError:
        return None
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        return None
    try:
        root.withdraw()
        root.attributes("-topmost", True)
        return filedialog.askdirectory(
            parent=root, title="Choose your existing project folder", mustexist=True)
    except tkinter.TclError:
        return None
    finally:
        root.destroy()


def _choice(prompt: str, allowed: tuple[str, ...], default: str) -> str:
    while True:
        answer = input(prompt).strip() or default
        if answer in allowed:
            return answer
        print("Please choose " + ", ".join(allowed) + ".")


@themed
def main() -> None:
    """Choose a folder and project type, then preview and confirm lint setup."""
    print(paint("\nExisting Project Setup\n", "panel"))
    print("Set up code checks for Python or JavaScript/TypeScript.")
    print("You will review changes before applying them. Tool installation is a separate choice.")
    try:
        while True:
            print("\n1) Browse for a project folder (default)\n\n2) Type or paste a folder path\n\n0) Exit\n")
            choice = _choice("Choose [1]: ", ("0", "1", "2"), "1")
            if choice == "0":
                print("Cancelled. Nothing changed.")
                return
            folder = browse_folder() if choice == "1" else None
            if folder is None:
                if choice == "1":
                    print("Folder browser unavailable. You can paste the folder path instead.")
                folder = input("Project folder (Enter to cancel): ").strip().strip('"')
            if not folder:
                print("Cancelled. Nothing changed.")
                return
            project = Path(folder).expanduser().absolute()
            if project.is_dir():
                break
            print("That folder does not exist. Please choose an existing project folder.")
        print(f"\nSelected project: {project}")
        print("\n1) Detect project type automatically (default)")
        print("\n2) Python - Ruff code checks")
        print("\n3) JavaScript / TypeScript - ESLint code checks (standalone npm project)")
        print("\n0) Cancel\n")
        stack = _choice("Project type [1]: ", ("0", "1", "2", "3"), "1")
        if stack == "0":
            print("Cancelled. Nothing changed.")
            return
        args = ["--setup-lint", str(project)]
        if stack != "1":
            args.extend(["--stack", {"2": "python", "3": "node_typescript"}[stack]])
        cli.main(args)
    except (EOFError, KeyboardInterrupt):
        print("\nSetup stopped.")
