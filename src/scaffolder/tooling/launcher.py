"""Menu for the complete scaffolder, with existing-project folder selection."""
from pathlib import Path

from .. import cli
from .existing import _choice, browse_folder


def choose_folder() -> Path | None:
    """Offer native browsing or a pasted path, without writing anything."""
    while True:
        print("\n1) Browse for the project folder (default)\n\n2) Paste a folder path\n\n0) Cancel\n")
        choice = _choice("Choose [1]: ", ("0", "1", "2"), "1")
        if choice == "0":
            return None
        folder = browse_folder() if choice == "1" else None
        if folder is None:
            if choice == "1":
                print("Folder browser unavailable. Paste the folder path instead.")
            folder = input("Folder (Enter to cancel): ").strip().strip('"')
        if not folder:
            return None
        path = Path(folder).expanduser().absolute()
        if path.is_dir():
            return path
        print("That folder does not exist. Choose an existing folder.")


def main() -> None:
    """Choose the complete new/existing workflow or a focused maintenance action."""
    print("\nScaff It\nSet up your project. Start building.\n")
    print("1) Add the full scaffold to an existing project (default)")
    print("   Choose a folder, answer setup questions, and preview missing files to add.")
    print("\n2) Create a new project\n   Choose project settings and preview a new project folder.")
    print("\n3) Set up code checks only\n   Configure Ruff or ESLint, with optional installation.")
    print("\n4) Add a changelog only\n   Keep an existing changelog or create a missing one.")
    print("\n0) Exit\n")
    try:
        action = _choice("Choose [1]: ", ("0", "1", "2", "3", "4"), "1")
        if action == "0":
            print("Cancelled. Nothing changed.")
            return
        if action == "2":
            print("\nChoose the parent folder where the new project folder will be created.")
            parent = choose_folder()
            if parent is None:
                print("Cancelled. Nothing changed.")
                return
            cli.main(["--out", str(parent)])
            return
        if action == "3":
            from .existing import main as lint_main
            lint_main()
            return
        folder = choose_folder()
        if folder is None:
            print("Cancelled. Nothing changed.")
            return
        if action == "1":
            print("\nFull existing-project setup: choose category, platform, technology, AI tools, and optional extras.")
            print("Existing files will be kept. Nothing is installed and Git history is preserved.")
            cli.main(["--scaffold-existing", str(folder)])
        else:
            cli.main(["--changelog", str(folder)])
    except (EOFError, KeyboardInterrupt):
        print("\nSetup stopped.")
