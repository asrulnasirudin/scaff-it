# Codex workflow

Codex reads `AGENTS.md` automatically; this file holds the detail. (Codex stops loading project instructions at about 32 KiB combined, so `AGENTS.md` stays short.)

1. Run the startup sequence in `AGENTS.md`.
2. Plan in `PLANS.md` or `phases/` before large changes.
3. Make small, verifiable changes; run the checks after each.
4. At a clean checkpoint update `CHECKPOINT.md`, then `DECISIONS.md` / `MEMORY.md` if needed, then recommend a Git checkpoint.
5. Ask before installs, deletions, structure changes, or edits to protected paths.
