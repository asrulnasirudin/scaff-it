"""Portable executable entry point with readable results and CLI compatibility."""
import json
import sys


def runtime_check() -> None:
    """Verify bundled resources and window support without showing a folder dialog."""
    import tkinter
    from .layers import load_catalog, TEMPLATES_DIR
    from .tooling.linting import bundled_ruff

    root = tkinter.Tk()
    try:
        root.withdraw()
        root.update_idletasks()
        tk_version = root.tk.call("info", "patchlevel")
    finally:
        root.destroy()
    tool = bundled_ruff()
    print(json.dumps({"frozen": bool(getattr(sys, "frozen", False)),
                      "profiles": len(load_catalog()), "tk": tk_version,
                      "templates": (TEMPLATES_DIR / "v2/agents.md").is_file(),
                      "bundled_ruff": bool(tool and tool.is_file())}))


def main(argv: list[str] | None = None) -> None:
    """Run flags directly, or keep a double-clicked interactive session readable."""
    args = sys.argv[1:] if argv is None else argv
    interactive = not args and bool(getattr(sys, "frozen", False)) and sys.stdin.isatty()
    try:
        if args == ["--check-runtime"]:
            runtime_check()
        elif args:
            from .cli import main as cli_main
            cli_main(args)
        else:
            from .tooling.launcher import main as launcher_main
            launcher_main()
    except SystemExit as exc:
        if interactive and isinstance(exc.code, str):
            print(exc.code)
            raise SystemExit(1) from None
        raise
    except KeyboardInterrupt:
        print("\nSetup stopped.")
    finally:
        if interactive:
            try:
                input("\nPress Enter to close this window.")
            except (EOFError, KeyboardInterrupt):
                pass
