# What belongs in the public repository

Keep the information another person or AI assistant needs to understand, build,
check, or continue Scaff It. Every tracked file must be suitable for public use.

## Shared project information

- `AGENTS.md`: working rules for AI assistants.
- `PROJECT_SPEC.md`: agreed product requirements.
- `.agent/MEMORY.md`: short, durable project context.
- `.agent/CHECKPOINT.md`: current status and validation limits, not a session log.
- `.agent/DECISIONS.md`: significant decisions and their reasons.
- `.agent/PLANS.md` and `.agent/QA_CHECKLIST.md`: next steps and validation needs.
- `.agent/CODEX.md`, check scripts, and useful context, phase, or review documents.
- User and developer guides, source code, tests, and build instructions.

The Markdown files under `src/templates/` are part of the product: Scaff It uses
them to create project guidance for its users. Keep them versioned. Do not ignore
all Markdown files or the entire `.agent/` folder.

## Local working material

Put drafts, chat transcripts, detailed working logs, old checkpoint snapshots,
recovery copies, raw references, branding explorations, and intermediate exports
under ignored `local/`. Its short `README.md` stays tracked to explain the folder.

The ignore list also excludes explicitly temporary `.agent/` folders
(`checkpoints`, `logs`, `scratch`, `transcripts`, and `tmp`), agent notes ending in
`.local.md` or `.scratch.md`, machine-specific assistant settings, build output,
test reports, caches, local environments, and root-level temporary/backup files.
Durable context and reviews remain eligible for version control.

Keep credentials and private personal information out of every shared document.
Ignoring a file is not access control, and it does not remove files already tracked
or erase earlier commits. Before publishing, review the staged file list and diff,
then run the repository safety and required validation checks.

Promote selected public assets deliberately. The current branding handoff exports
are local material; the selected geometry, colours, and wording are recorded in
the [brand guide](BRANDING.md). Publishing source changes does not rebuild or
replace a previously released Windows download.
