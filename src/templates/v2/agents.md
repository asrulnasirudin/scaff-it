# @@NAME@@: agent instructions

@@CATEGORY@@ · @@PLATFORMS@@ · @@TARGETS@@ · stack: @@STACK@@ · state: @@STATE@@

## Startup sequence (every new session)
1. Read this file, `PROJECT_SPEC.md`@@STARTUP_AGENT@@.
2. Inspect Git status; confirm the branch and worktree (see Git below).
3. Continue only from verified facts. Chat history is never the handoff.

## Files and what they answer
- `PROJECT_SPEC.md`: what we are building.
- `AGENTS.md` (this file): how to work.
- `CHANGELOG.md`: notable changes and dated version history (Keep a Changelog / Semantic Versioning).
@@AGENT_FILES@@
@@PRECEDENCE@@ Safety rules in this file always apply.

## Folder map
@@FOLDER_MAP@@

## Commands
```
@@COMMANDS@@
```
Verify: run the checks above@@CHECK_STEP@@, then walk `@@QA_PATH@@`.
Never install dependencies or run installers without approval.

## Conventions
@@CONVENTIONS@@

## Don'ts
@@DONTS@@

## Safety
- Assume every tracked file may be published. Secrets never enter the repository, public or private.
- Local-only (git-ignored): @@LOCAL_ONLY@@
- Watch for files named: @@WATCH@@. Warn the user; don't delete or move them.
- Protected paths (no edits without approval): @@PROTECTED@@
- Large files over @@LARGE_MB@@ MB: ask before adding.

## Git
@@GIT_SECTION@@
Commit policy: `ask`: recommend a checkpoint when a task is validated; the owner decides whether to commit. Never push, create remotes, rewrite history or delete branches without being asked.

## Toolchain
@@TOOLCHAIN@@
