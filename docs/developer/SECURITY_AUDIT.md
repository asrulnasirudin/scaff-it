# Security verification and scope

Public baseline reviewed: 2026-11-04. Scaff It 0.1.0.

The public repository starts from a reviewed source snapshot with independent Git
history and public/noreply attribution. Local working material, recovery backups,
installed environments, caches, and previous Git databases are excluded.

## Checks

- Scan all candidate and staged files for credential patterns without emitting values.
- Review documentation, metadata, filenames, and commit identity for private details.
- Run Ruff, unittest, readiness, safety, and whitespace checks.
- Run hosted checks on pushes and pull requests with pinned Actions, read-only
  repository permissions, and checkout credentials not retained on disk.
- Build the portable app with security-patched Python 3.14.10 and retain Python,
  Tcl/Tk, Ruff, and PyInstaller notices. Verify ZIP integrity and a SHA-256 checksum.
- Verify the extracted app's runtime/Tk/resources, CLI/menu, dry-run, new/existing
  project operations, file preservation, and offline lint pass/failure without
  Python, Git, or npm on PATH.

## Limits

Heuristic scanning cannot prove the absence of every encoded, split, unknown-format,
or semantically private value. Review future diffs before publishing. Existing
ESLint configuration executes code; run tooling only in projects you trust.
The optional Node dependency graph needs a fresh audit when resolved or updated;
no Node lockfile here establishes a current transitive dependency inventory.

Filesystem rechecks are not atomic protection against a hostile process changing
paths concurrently. Clean Windows profile/VM and real symlink/junction acceptance
remain open. The unsigned initial release is not a penetration-test certification.

## Initial release verification

- Python 3.14.10 regression suite: 143 cases, 142 passed and one existing Windows symlink-privilege skip.
- Ruff, readiness, repository safety, and whitespace checks pass.
- Extracted Windows ZIP passes runtime/Tk/resources, menu/help, no-host-tools PATH, dry-run, real new/existing creation, preservation, and offline Ruff pass/failure checks.
- All 42 profiles, current scanner content, component notices, and standalone package security documentation are retained.
- ZIP size: 24597880 bytes.
- ZIP SHA-256: `b1ce46c98269e20b42675092522d23467fc221bf5340470cff4d3a3d910b6937`.
- Hosted checks and public asset bytes are verified as part of publication; release checksum accompanies the download.
