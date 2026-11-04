"""Build a portable Windows folder, retain component notices, and write a shareable ZIP.

Run with the isolated build interpreter after installing requirements-build.txt.
The matching Python license HTML must be downloaded into build/ before running.
"""
import importlib.metadata
import json
import platform
import shutil
import sys
import zipfile
from pathlib import Path


def main() -> None:
    """Bundle local runtime resources; never install tools or overwrite a prior package."""
    if sys.platform != "win32" or platform.machine().upper() != "AMD64":
        raise SystemExit("Build this package with 64-bit Python on Windows.")
    if sys.version_info[:3] < (3, 14, 10):
        raise SystemExit("Use security-patched Python 3.14.10 or newer for portable builds.")
    import PyInstaller.__main__

    root = Path(__file__).resolve().parent.parent
    output = root / "dist/windows/Scaff It"
    archive = root / "dist/Scaff-It-Windows.zip"
    if output.exists() or archive.exists():
        raise SystemExit("A Windows package already exists. Preserve it or choose a fresh output before rebuilding.")
    python_license = root / "build" / f"python-{platform.python_version()}-license.html"
    if not python_license.is_file():
        raise SystemExit(f"Download the matching official Python license page to {python_license} first.")
    ruff = Path(sys.executable).parent / "ruff.exe"
    if not ruff.is_file():
        raise SystemExit("Install the approved build requirements in this build environment first.")
    PyInstaller.__main__.run([
        str(root / "src/windows_app.py"), "--name", "Scaff It", "--onedir", "--console",
        "--noupx", "--paths", str(root / "src"),
        "--distpath", str(root / "dist/windows"),
        "--workpath", str(root / "build/windows-work"), "--specpath", str(root / "build/windows-spec"),
        "--add-data", f"{root / 'src/layers'}:layers",
        "--add-data", f"{root / 'src/templates'}:templates",
        "--add-binary", f"{ruff}:tools",
    ])
    shutil.copy2(root / "LICENSE", output / "LICENSE")
    shutil.copy2(root / "CHANGELOG.md", output / "CHANGELOG.md")
    notices = output / "THIRD_PARTY_NOTICES"
    notices.mkdir()
    shutil.copy2(Path(sys.base_prefix) / "LICENSE.txt", notices / "PYTHON-LICENSE.txt")
    shutil.copy2(python_license, notices / "PYTHON-THIRD-PARTY-LICENSES.html")
    for dist_name in ("ruff", "pyinstaller"):
        dist = importlib.metadata.distribution(dist_name)
        for item in dist.files or []:
            if Path(item).name.lower() in {"license", "license.txt", "copying.txt", "license.terms"}:
                source = Path(dist.locate_file(item))
                if source.is_file():
                    shutil.copy2(source, notices / f"{dist_name.upper()}-{source.name}")
    tcl_root = Path(sys.base_prefix) / "tcl"
    for source in tcl_root.rglob("license.terms"):
        if "demos" not in source.parts:
            shutil.copy2(source, notices / ("TCL-TK-" + "-".join(source.relative_to(tcl_root).parts)))
    # Python 3.14 ships Tcl/Tk 9 library data and notices inside ZIPs.
    for source in tcl_root.glob("libt*.zip"):
        with zipfile.ZipFile(source) as library:
            for name in library.namelist():
                if Path(name).name == "license.terms":
                    (notices / f"TCL-TK-{source.stem}-license.terms").write_bytes(library.read(name))
    if len(list(notices.glob("TCL-TK-*"))) < 2:
        raise SystemExit("Tcl and Tk notices are missing; do not distribute this build.")
    guide = (root / "docs/user/README.md").read_bytes()
    try:
        guide_text = guide.decode("utf-8")
    except UnicodeDecodeError:
        guide_text = guide.decode("cp1252")
    guide_text = guide_text.replace("../developer/SECURITY_AUDIT.md", "SECURITY_SCOPE.md")
    (output / "USER_GUIDE.md").write_text(guide_text, encoding="utf-8")
    shutil.copy2(root / "docs/developer/SECURITY_AUDIT.md", output / "SECURITY_SCOPE.md")
    (output / "START HERE.txt").write_text(
        "Scaff It - Kriio Works\nSet up your project. Start building.\n\n"
        "1. Extract the complete ZIP to a folder you can write to.\n"
        "2. Double-click Scaff It.exe. No Python installation is needed.\n"
        "3. Choose a menu action, browse for a folder, and review changes before approval.\n\n"
        "Keep the entire folder together, including _internal. Do not run from inside the ZIP.\n"
        "Windows 64-bit is required. No administrator installation is needed.\n\n"
        "Included: full new/existing-project setup, templates, folder browser, changelog tools, "
        "and Ruff code checks. Python lint checks use the included Ruff executable without downloads.\n"
        "Git is optional. Node.js/npm is only needed for optional JavaScript/TypeScript lint installation; "
        "other project development tools are separate from the scaffolder.\n\n"
        "The bundled runtime runs this app; it does not install Python for running your own applications.\n"
        "The advanced command-line examples in USER_GUIDE.md can use Scaff It.exe "
        "in place of python src/new_project.py.\n\n"
        "The app is unsigned. Windows may ask you to confirm its publisher before running it.\n"
        "Clean Windows user-profile and real symlink/junction acceptance remain outstanding.\n\n"
        "Scaffolder: MIT, copyright (c) 2026 Kriio Works. Retain LICENSE. "
        "Bundled components have their own notices in THIRD_PARTY_NOTICES.\n",
        encoding="utf-8")
    components = {name: importlib.metadata.version(name) for name in (
        "pyinstaller", "ruff", "pyinstaller-hooks-contrib", "altgraph", "packaging", "pefile", "pywin32-ctypes")}
    (output / "BUILD-INFO.json").write_text(json.dumps({
        "name": "Scaff It", "version": "0.1.0",
        "python": platform.python_version(), "platform": "Windows x64", "components": components,
        "python_license_source": f"https://docs.python.org/release/{platform.python_version()}/license.html",
        "format": "portable directory", "entry": "Scaff It.exe"}, indent=2) + "\n", encoding="utf-8")
    shutil.make_archive(str(archive.with_suffix("")), "zip", root_dir=output.parent, base_dir=output.name)
    print(f"Portable folder: {output}\nShareable ZIP: {archive}")


if __name__ == "__main__":
    main()
