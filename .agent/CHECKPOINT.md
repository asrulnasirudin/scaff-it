# Checkpoint

## Current source - 2026-11-04

- Public baseline: Scaff It 0.1.0. The existing Windows download remains unchanged by source updates.
- Selected identity: folder with flowing S and a small square rounded only at bottom-right. Gold tab; cream #F0E8D0, gold #B09050, garnet #A02838, burgundy #6A1828, ink #200808. See docs/developer/BRANDING.md.
- Source launcher and CLI use the shared palette in supported interactive terminals. Logs, NO_COLOR, dumb terminals, and unsupported consoles stay plain. Windows folder dialogs retain system styling.
- Keep shared AI guidance and product templates public. Temporary drafts, transcripts, old checkpoints, local settings, exports, and generated reports remain ignored. See docs/developer/PUBLICATION.md.
- Selected branding exports remain in ignored local/; public asset integration and a portable rebuild are separate work.
- Validation: 149 tests ran successfully with one existing Windows link-permission skip; readiness, repository safety, whitespace, SVG/PNG/ICO, and bundle checks passed. Windows terminal colour support was verified. Ruff is unavailable locally; the protected GitHub check runs the pinned checker.
- Local restricted execution cannot create temporary Git config files; regression tests pass with normal permissions.
- Publish source updates through a pull request and required checks; keep the public origin and noreply identity. No Windows release rebuild is included.
- Open acceptance work: clean Windows profile/VM, real links/junctions, and optional Node dependency re-audit when dependencies change.
