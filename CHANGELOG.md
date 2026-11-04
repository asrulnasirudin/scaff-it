# Changelog

All notable changes are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Selected public light/dark logos and an illustrated project-folder preview for the GitHub README.
- Brand guide for the selected folder logo, flowing S ribbon, gold tab, and small square with a rounded bottom-right corner.
- Shared cream, gold, garnet, burgundy, and ink palette for interactive menu styling, with plain output for logs, unsupported consoles, and NO_COLOR.

### Changed

- Vertically centre the Scaff It wordmark with the folder symbol in both public logo variants.
- Restructure the GitHub README to match FrameShelf's product-first format, with user/developer quick starts, feature and documentation tables, feedback, and release status.
- Introduce Scaff It in plain language around organised project folders and shared information for AI assistants.
- Update the selected logo tab, brand board, and handoff exports from teal to gold using the shared interface palette.

### Security

- Exclude temporary AI notes, transcripts, checkpoint snapshots, machine-specific assistant settings, and test reports from version control while retaining shared project guidance and product templates.

## [0.1.0] - 2026-11-04

### Added

- Publish Scaff It: Set up your project. Start building.
- Guided Windows menu and CLI for new projects and additive existing-project scaffolding.
- Previewable profiles, documentation, AI handoffs, project descriptors, and changelogs.
- Optional local Git initialization and separately consented Ruff/ESLint code checks.
- Portable Windows x64 download with Python 3.14.10, Tcl/Tk, native Ruff, and component notices.
- Pinned GitHub Actions for lint, tests, readiness, and repository safety.

### Security

- Scan candidate and staged files, example configuration, and large/non-UTF-8 files for credential patterns without printing values.
- Reject linked destinations, preserve existing files, and restrict cleanup to unchanged run-created items.
- Start public history from a reviewed source snapshot using public/noreply commit attribution.
