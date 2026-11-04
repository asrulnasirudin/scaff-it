# Using Scaff It

## Portable Windows app (no Python installation)

Extract the complete **Scaff-It-Windows.zip**, then double-click **Scaff It.exe**. Keep the **_internal** folder next to the executable. Windows x64 is required; no administrator installation is needed. The app is unsigned, so Windows may show a publisher confirmation.

The full menu, profiles, templates, native folder browser, and Ruff checker are included. Python code checks can use bundled Ruff without downloads or a separate Python installation, after you choose to run the check. Git is optional. JavaScript/TypeScript lint installation still needs Node.js/npm; other application development tools are separate from the scaffolder.

For advanced commands below, replace **python src/new_project.py** with **Scaff It.exe** when using the portable build. The source scripts and CMD launchers described below require Python; the EXE does not.

## Run from Python source

Run from the repository folder with Python 3.11 or newer:

```powershell
python src/new_project.py
```

Choose the project name and parent folder, then answer questions about the category, target platform, host application, technology stack, AI tools, distribution, optional features, and Git. Choose an undecided stack when appropriate. Tool installation is optional and requires a separate opt-in.

Review the proposed tree and security summary. Choose C to create, M to modify an answer, B to revisit the last question, or X to cancel. Cancelling writes nothing. Missing flag values are asked interactively even when `--yes` is supplied.

Preview an example without creating it (the parent folder is an example relative location):

```powershell
python src/new_project.py "Demo" --description "Example project" --out ../projects --category tool --platform windows --target none --stack python --state new --ai codex --distribution none --features none --no-git --dry-run
```

Remove `--dry-run` to review and create. Add `--yes` only when you intentionally want to bypass the confirmation menu. See `python src/new_project.py --help` for all flags.

The new-project workflow requires a new or empty destination. To add missing scaffold files to an existing project while preserving its files, use the complete launcher described below. Conflicting new-project destinations are refused. Compatible partial creation can be resumed by repeating the same inputs. On failure, cleanup is offered for unchanged items created by that run; keep the partial output if uncertain.

Git initialization is optional. A first commit is off by default; `--first-commit` explicitly requests one after the safety check and requires your own Git identity. The tool never pushes or configures remotes. If Git initialization fails, the generated project files may still exist; read the reported error.

After creation, open the generated PROJECT_SPEC.md and fill its outstanding requirements before starting application development. Follow AGENTS.md and the generated QA checklist.

Profiles describe target technologies; their presence does not certify a particular tool installation or host version. Optional lint setup and installation are supported below; general existing-project migration is not supported. This scaffolder is distributed under MIT, copyright 2026 Kriio Works. Include its LICENSE when sharing the source; separately downloaded tools retain their own licenses.

## Understanding the choices

Every listed project category, platform, host program, technology, AI tool, delivery option, and optional extra includes a plain-language description. Technology choices explain what you can build with them. Choosing a technology records your plan; it does not install its tools.

For example, Python is described as a way to build scripts, automation, or other programs. Tauri is described as a way to build a desktop app with web-style screens and Rust code behind them. If you do not know which technology to use, choose `0` for Undecided.

Menus show the option name in brackets so you can type it instead of its number. For multiple selections, separate numbers or bracketed names with commas. The menu states what Enter will select. Where allowed, `0` explicitly chooses None or Undecided even if another option is the default. Required host-program selections do not offer None.

Git means local change history, a branch is a separate line of changes, and a commit is a saved snapshot. The Git questions explain what Yes and No do, and describe each workflow before you choose. The final preview explains Create, Modify, Back, and Cancel before asking for approval.

Questions are separated by divider lines and headings. Each optional extra has its own numbered block and Yes/No prompt. Descriptions wrap to fit the terminal, up to 88 characters per line, with blank space between options. This applies when revisiting questions through Modify as well.

## Included code checks

Choosing Python adds Ruff configuration and `requirements-dev.txt`. After approving development-tool installation, run `python -m pip install -r requirements-dev.txt`, then `python -m ruff check .`.

Choosing Node.js + TypeScript adds ESLint configuration and a private `package.json`. After approving `npm install`, run `npm run lint`. This starter configuration targets Node; browser and framework rules can be added once those choices are made.

The preview shows these files before creation. Installation is optional as described below; other stack profiles are unchanged.

## Complete Windows launcher

Double-click **Scaff It.cmd** in the scaffolder folder. Python 3.11 or newer must already be installed. **Setup Existing Project.cmd** opens the same menu.

- **Add the full scaffold to an existing project:** browse for your project folder, then answer the category, platform, host application, technology, AI-tool, distribution, and optional-extras questions. Review files to add and existing scaffold paths to keep, then approve the additions.
- **Create a new project:** choose its parent folder, answer the guided questions, and review the preview before creation.
- **Set up code checks only:** configure lint tools with a separate optional installation choice.
- **Add a changelog only:** create a missing changelog while keeping an existing one.

Existing-project scaffolding adds missing documentation, instructions, AI handoff files, selected profile configuration, and folders. It keeps existing files exactly as they are, including README, specifications, package manifests, ignore rules, agent notes, and any descriptor. It does not move application code, initialize Git, or install packages. Existing history and settings are preserved.

Review generated commands, folder roles, and ignore rules against the actual project. Existing files are not merged with templates: if an existing README or agent-instruction file needs new guidance, edit it separately. An existing descriptor keeps its historical baseline; a missing descriptor records only newly added files. Invalid destinations, linked scaffold paths, case collisions, and file/folder conflicts are refused. After a partial failure, review the reported files before rerunning to add the remaining missing files.

For command-line use, preview or apply the full existing-project setup:

```powershell
python src/new_project.py --scaffold-existing "C:/Projects/MyProject" --dry-run
python src/new_project.py --scaffold-existing "C:/Projects/MyProject"
```

## Optional installation and existing projects

### Code checks through the menu

Double-click **Scaff It.cmd** and choose **Set up code checks only**. Browse for the project folder or paste its path, choose automatic detection or a project type, review configuration, then separately choose whether to install the tools.

### Command-line options

After creating a supported project interactively, choose Yes at “Install development tools and run the lint check now?” to download tools and check the code. Enter means No. `--yes` alone never authorizes installation. Add `--install-tools` to explicitly authorize it, or `--no-install-tools` to suppress the question.

For one existing project, run from the scaffolder folder (replace the example path):

```powershell
python src/new_project.py --setup-lint "C:/Projects/MyProject" --dry-run
python src/new_project.py --setup-lint "C:/Projects/MyProject"
python src/new_project.py --setup-lint "C:/Projects/MyProject" --install-tools --yes
```

The first command previews only. The second previews and asks before changing configuration, then separately offers installation. The third explicitly authorizes both. Add `--stack python` or `--stack node_typescript` when detection is ambiguous or the folder has no dependency manifest. Run again to retry a failed installation.

Python gets Ruff in `.venv-lint`, independent of the application's environment. To check again on Windows, use `.venv-lint/Scripts/python.exe -m ruff check .`. JavaScript/TypeScript uses `npm install --ignore-scripts --include=dev`, which installs the project's declared application and development dependencies and may update its lockfile, then runs local ESLint. Development tools contributed by selected layers are included even when the environment normally omits development packages. Existing lint scripts, rules and declared versions are kept. For new configurations, `npm run lint` runs ESLint.

This supports Python and standalone npm projects. Mixed-language folders need an explicit stack choice; other package managers, workspaces, legacy ESLint and recognized alternative linters require manual setup. New JavaScript configuration assumes Node; adapt browser/framework globals as needed. Setup never auto-fixes source code. A nonzero check result may mean existing code needs attention; installation/configuration is retained.

If the package manifest or npm lockfile changes after preview, setup stops before applying configuration or starting installation. Review the change and run setup again. No dependency lifecycle scripts or automatic source fixes are run.


## Changelog and version iterations

Every new project starts with one root CHANGELOG.md containing the standard
Keep a Changelog header, links to Keep a Changelog 1.1.0 and Semantic Versioning
2.0.0, and an empty Unreleased section. Generated AGENTS.md tells coding agents
to record notable changes there as they work. Do not copy the example project's
history or create a release entry for an iteration with no changes.

Group entries under only the relevant headings: Added, Changed, Deprecated,
Removed, Fixed, or Security. For example:

```markdown
## [Unreleased]

### Added

- Export reports as PDF.

### Fixed

- Preserve the selected date when reopening a report.
```

To create the file in an existing project, run this from the scaffolder folder:

```powershell
python src/new_project.py --changelog "C:/Projects/MyProject" --dry-run
python src/new_project.py --changelog "C:/Projects/MyProject"
```

An existing file is kept exactly as it is. Add real pending change entries under
Unreleased, then preview a version release:

```powershell
python src/new_project.py --changelog "C:/Projects/MyProject" --release 1.2.3 --release-date 2026-11-02 --dry-run
```

Remove --dry-run to confirm the change, or use --yes to apply it without a prompt.
The result keeps Unreleased at the top and moves its entries into
`## [1.2.3] - 2026-11-02`, above older versions. With no --release-date, today's
local date is used. Choose the actual version yourself: major for incompatible
API changes, minor for compatible features, patch for compatible fixes. Use a
full version such as 1.2.3 or 1.2.3-rc.1, without a v prefix.

Empty changes, duplicate or older versions, invalid dates, linked paths, and
ambiguous version headings are refused. No other project files are regenerated;
package versions, descriptor baseline hashes, Git commits, tags, and publishing
remain separate. Existing comparison-link definitions are retained literally;
update their URLs yourself if needed. This command does not install anything.


## Checking before sharing

Run `python .agent/safety_check.py` in a generated project with agent support.
It checks candidate and staged files, including example environment-file contents,
and reports locations without printing secret values. Keep real values in ignored
local files. Also review documents and Git commit name/email before publishing:
heuristics cannot detect every kind of private information. Existing ZIPs need to
be rebuilt to include fixes. See [the security audit](../developer/SECURITY_AUDIT.md)
for remaining package and GitHub findings.
