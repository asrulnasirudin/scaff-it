# Scaff It: project specification

Current public baseline: 2026-11-04. Release: 0.1.0.

## Identity and purpose

Scaff It is a Windows project scaffolding tool with a guided menu, a command-line
interface, and importable Python logic. Its tagline is: Set up your project. Start building.
Prepare consistent project folders for individual developers and project owners,
including source/tests, requirements, documentation, and AI instructions.

## Supported behavior

- Preview before writing; allow modification, cancellation, and dry-run.
- Compose validated TOML layers and text templates for categories, platforms,
  stacks, host applications, AI tools, features, and distribution plans.
- Generate a machine-readable descriptor with selected profiles and managed hashes.
- Add missing scaffolding to an existing project without replacing existing files,
  reorganizing source, or altering its Git settings/history.
- Generate a changelog and support explicit initialization and version releases
  in existing projects while retaining previous content and line endings.
- Offer optional Python/Ruff and standalone npm/ESLint lint setup. Preserve existing
  configuration and separate file approval from package-download/check consent.
- Support optional local Git initialization on main. No first commit by default;
  an explicitly requested first commit must pass the repository safety check.
- Keep the Python runtime standard-library only; optional development/build tools
  are declared separately. Source mode requires Python 3.11 or newer.

## Safety and boundaries

Validate names, relative paths, Windows reserved names, case collisions, destination
conflicts, and links/reparse points. Use exclusive creation and rechecks to reduce
replacement risk. Report partial writes; cleanup is opt-in and limited to unchanged
items created by the run. Do not claim atomic protection against hostile concurrent
filesystem changes. Preserve existing project files and user edits.

Keep credentials and private information out of tracked files and agent notes.
Keep local working material under ignored local/. Repository scanning reports
locations and rules without printing matched values. It is heuristic, not a proof
that every possible secret or private detail is absent.

The product does not push to hosting services, collect telemetry, generate finished
application functionality, install packages without consent, or perform general
project migrations. Profiles targeting other platforms do not establish tested
operation of the scaffolder on those platforms.

## Distribution and validation

Provide a portable Windows x64 ZIP containing Scaff It.exe, Python 3.14.10 or newer,
Tcl/Tk, all profiles/templates, native Ruff, component notices, and start instructions.
Recipients extract the entire ZIP and keep _internal alongside the executable.
The portable runtime does not install Python for developing generated applications.

Run lint, unittest regressions, readiness, repository safety, and whitespace checks.
Validate the extracted ZIP's runtime/Tk/resources, dry-run, actual new/existing
creation, preservation, and offline Ruff pass/failure without host tools on PATH.
Clean Windows profile/VM and real symlink/junction acceptance remain open.

## Licensing and maintenance

Scaffolder code, profiles, templates, tests, and documentation use MIT, copyright
2026 Kriio Works. Retain third-party notices in distributions. Generated applications
need their own licensing decisions. Maintain notable changes under Unreleased and
use dated Semantic Version entries for actual releases. Normal commit/push policy
remains ask; the owner authorized the initial public repository and 0.1.0 download.
