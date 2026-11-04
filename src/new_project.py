#!/usr/bin/env python3
"""Launch the v2 new-project scaffolder with Python 3.11 or newer."""
import sys


def main() -> None:
    """Check the interpreter and run the command-line interface."""
    if sys.version_info < (3, 11):
        sys.exit("This scaffolder needs Python 3.11 or newer.")
    from scaffolder.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
