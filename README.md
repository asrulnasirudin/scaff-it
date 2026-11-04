# Scaff It

**Set up your project. Start building.**

Scaff It prepares a consistent project folder with source and test locations,
documentation, requirements, and instructions for AI coding tools. Answer guided
questions, review the proposed files, and create the project when you are ready.
You can also add missing scaffolding to an existing project while preserving its files.

[Download for Windows](https://github.com/asrulnasirudin/scaff-it/releases/latest) ·
[User guide](docs/user/README.md) · [Developer guide](docs/developer/README.md)

## Quick start on Windows

1. Download **Scaff-It-Windows.zip** from [Releases](https://github.com/asrulnasirudin/scaff-it/releases/latest).
2. Extract the entire ZIP into a writable folder.
3. Open **Scaff It.exe** and choose an action.
4. Choose your project folder and tools, review the preview, then approve creation.

Keep the `_internal` folder beside the executable. The portable app includes
Python, folder browsing, templates, and Ruff; recipients do not need to install
Python or use an administrator installer. The app is unsigned, so Windows may
show a publisher warning. A SHA-256 checksum accompanies the release download.

## What it does

- Creates new projects through guided questions or command-line options.
- Adds missing scaffold files to existing projects without replacing their content.
- Supports project categories, platforms, technology stacks, host applications,
  AI tools, optional features, and distribution plans through 42 profiles.
- Generates project requirements, documentation, changelogs, and AI handoff files.
- Previews changes and rejects unsafe paths, conflicts, and linked destinations.
- Offers separately consented Python/Ruff or npm/ESLint setup and code checks.
- Offers optional local Git initialization. No first commit unless explicitly requested.

It prepares project structure; it does not generate a finished application.
Git is optional. Node.js/npm is needed only for optional JavaScript tooling.
Generated projects need their own appropriate development runtimes and licenses.

## Run from source

Windows and Python 3.11 or newer are required for the source launcher.
Runtime code uses Python's standard library.

```powershell
python src/project_scaffolder.py
```

You can also double-click **Scaff It.cmd** or use the direct CLI:

```powershell
python src/new_project.py --help
python src/new_project.py Demo --out ../projects --category tool --platform windows --target none --stack python --state new --ai codex --distribution none --features none --no-git --dry-run
```

## Development and verification

```powershell
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m unittest discover -s tests -v
python .agent/check.py
python .agent/safety_check.py
```

Install development tools only when you intend to. GitHub Actions runs these
checks on pushes and pull requests. See [the build guide](docs/developer/README.md)
for the portable Windows package and [security scope](docs/developer/SECURITY_AUDIT.md)
for the checks and their limits. Clean Windows profile/VM and real junction testing
remain open; the release is an initial public version.

## License

MIT, copyright 2026 Kriio Works. See [LICENSE](LICENSE).
Bundled components retain their own notices in the portable package.
The scaffolder does not automatically license the applications you create.
