# Scaff It: agent instructions

Command-line tool or library · Windows · no host application · stack: Python · state: New project

## Startup sequence (every new session)
1. Read this file, `PROJECT_SPEC.md`, `.agent/MEMORY.md`, `.agent/CHECKPOINT.md`, `.agent/PLANS.md`.
2. Inspect Git status; confirm the branch and worktree (see Git below).
3. Continue only from verified facts. Chat history is never the handoff.

## Files and what they answer
- `PROJECT_SPEC.md`: what we are building.
- `AGENTS.md` (this file): how to work.
- `.agent/MEMORY.md`: durable context a new agent should know.
- `.agent/CHECKPOINT.md`: where the project is right now.
- `.agent/DECISIONS.md`: why decisions were made.
- `.agent/PLANS.md`: what comes next.
- `.agent/QA_CHECKLIST.md`: what must be validated.

Precedence if they disagree: `PROJECT_SPEC.md` > `.agent/DECISIONS.md` > `.agent/CHECKPOINT.md` > `.agent/MEMORY.md`. Safety rules in this file always apply.

## Folder map
- `src/`: Product source code.
- `tests/`: Automated tests.
- `build/`: Intermediate build output. Created by build tools; safe to delete. (created by tooling later)
- `dist/`: Final deliverables. Created by build/packaging tools. (created by tooling later)
- `docs/user/`: End-user documentation.
- `docs/developer/`: Maintainer documentation: architecture, conventions, how it is built.
- `.agent/`: AI orchestration: memory, checkpoint, plans, decisions, QA.
- `local/`: Local-only working material. Git-ignored; never committed.
- `.project.json`: machine-readable project descriptor (no secrets)

## Commands
```
python -m ruff check .
python -m unittest discover -s tests -v
```
Verify: run the checks above, then `python .agent/check.py`, and `python .agent/safety_check.py` before any commit, then walk `.agent/QA_CHECKLIST.md`.
Never install dependencies or run installers without approval.

## Conventions
- Follow the startup sequence in this file before changing anything.
- Keep this file short; put detail in linked documents.
- Keep shared AI guidance concise and public-safe. Put temporary notes and old checkpoints in ignored local/; see docs/developer/PUBLICATION.md.
- Record notable changes in root `CHANGELOG.md` under `Unreleased`, using relevant Added, Changed, Deprecated, Removed, Fixed, or Security sections. For actual version releases, use dated Semantic Version headings, newest first; retain Unreleased and preserve earlier history. Skip empty releases and never invent history.
- Keep a thin command-line layer over importable logic so the logic can be tested alone.
- No hard-coded drive letters or backslash paths; build paths with the language's path API.
- Type-hint public functions; keep modules small and importable without side effects.
- Update `.agent/CHECKPOINT.md` at every clean checkpoint, not mid-task.
- Record why a significant decision was made in `.agent/DECISIONS.md`.
- Put detail in `.agent/context/` and link to it from here.
- Heavy production files live in `local/production-assets/`; track only small, required assets in `assets/`.

## Don'ts
- Never read, print, copy or commit secrets (keys, tokens, passwords, `.env`, credentials).
- Never put secrets or private personal data into any document, including notes written for other agents.
- Ask before deleting files, adding dependencies, installing anything, or changing the folder structure.
- Never edit a protected path (listed below) without explicit approval.
- Never commit or push unless `git.commit_policy` in `.project.json` allows it; recommend a checkpoint instead.
- Don't start building until `PROJECT_SPEC.md` has no TODO or TO CONFIRM left.
- Never put secrets or private personal data into `.agent/MEMORY.md`; never paste chat transcripts into it.

## Safety
- Assume every tracked file may be published. Secrets never enter the repository, public or private.
- Local-only (git-ignored): `local/`
- Watch for files named: `credentials.*`, `secrets.*`, `*.aep`, `*.prproj`, `*.psb`, `*.mov`, `*.mp4`, `*.mxf`, `*.wav`, `*.exr`. Warn the user; don't delete or move them.
- Protected paths (no edits without approval): none declared
- Large files over 5 MB: ask before adding.

## Git
Workflow: `simple`. Work on `main`; keep changes small and checked. Recommend a commit when a task is validated; the owner decides whether to commit.
Commit policy: `ask`: recommend a checkpoint when a task is validated; the owner decides whether to commit. Never push, create remotes, rewrite history or delete branches without being asked.

## Toolchain
- python: >=3.11
