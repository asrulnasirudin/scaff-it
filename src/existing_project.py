#!/usr/bin/env python3
"""Launch guided lint setup for an existing project."""
import sys


def main() -> None:
    """Check Python before importing the setup wizard."""
    if sys.version_info < (3, 11):
        sys.exit("This scaffolder needs Python 3.11 or newer.")
    from scaffolder.tooling.existing import main as wizard_main
    wizard_main()


if __name__ == "__main__":
    main()
