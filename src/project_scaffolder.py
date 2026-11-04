#!/usr/bin/env python3
"""Launch the complete project scaffolder menu."""
import sys


def main() -> None:
    """Check Python and open the guided launcher."""
    if sys.version_info < (3, 11):
        sys.exit("This scaffolder needs Python 3.11 or newer.")
    from scaffolder.tooling.launcher import main as launcher_main
    launcher_main()


if __name__ == "__main__":
    main()
