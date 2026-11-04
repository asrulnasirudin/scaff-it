# Maintaining Scaff It

## Layout

- Scaff It.cmd and src/project_scaffolder.py open the complete Windows menu.
- Setup Existing Project.cmd is an alternate entry point.
- src/new_project.py exposes the direct command-line interface.
- src/scaffolder/ contains intake, profile loading, resolution, rendering, path safety, creation/recovery, existing-project adoption, Git, and lint adapters.
- src/layers/ contains TOML profiles; src/templates/v2/ contains document templates.
- tests/ contains standard-library unittest cases. .agent/ holds concise maintenance context.

Resource lookup is relative to modules. Keep layers and templates alongside the
package. Keep technology-specific rules in profile data. Existing-project setup
preserves files, descriptors, and Git history. Existing ignore rules need owner
review. Filesystem rechecks do not promise race-free concurrent-path protection.

## Checks

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m unittest discover -s tests -v
python .agent/check.py
python .agent/safety_check.py
git diff --check
```

Install development dependencies only with consent. Tests use temporary projects;
first-commit behavior is mocked. A Windows symlink case skips if privileges are
unavailable. GitHub Actions runs the source checks on Windows with Python 3.14.10.
Templates use LF in fresh checkouts to keep generation and hashes deterministic.

## Portable Windows build

Use official 64-bit Python 3.14.10 or newer on Windows. Create an isolated build
environment, install requirements-build.txt, and download the matching official
Python license page to build/python-VERSION-license.html.

```powershell
python -m venv build/windows-venv
build/windows-venv/Scripts/python.exe -m pip install -r requirements-build.txt
build/windows-venv/Scripts/python.exe tools/build_windows.py
```

Output: dist/windows/Scaff It/ and dist/Scaff-It-Windows.zip. Preserve prior output
before rebuilding; the script refuses to overwrite it. Keep _internal and notices
beside Scaff It.exe. Python 3.14 Tcl/Tk 9 notices are inside runtime library ZIPs;
the build retains them explicitly. Do not reexecute the frozen bootloader as a
Python interpreter. Python lint checks use bundled native Ruff after consent.

Verify the extracted ZIP with no Python/Git/npm on PATH: --check-runtime, --help,
menu cancellation, dry-run, real new/additive creation, preservation, and offline
Ruff pass/failure. Record the SHA-256 checksum and verify the actual public asset
bytes after publishing. Clean-profile/VM and real junction acceptance remain open.

See [security scope](SECURITY_AUDIT.md) and [license provenance](PROVENANCE.md).
