#!/usr/bin/env python3
"""Small readiness check. Run:  python .agent/check.py
Fails on: missing required documents, TODO / TO CONFIRM left in must-fill documents,
changes under protected paths. Warns when MEMORY/CHECKPOINT grow too long.
Standard library only; makes no network calls and changes nothing.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUST_FILL = @@MUSTFILL@@
REQUIRED = ["AGENTS.md", "PROJECT_SPEC.md", ".project.json"]
LIMITS = {".agent/MEMORY.md": 150, ".agent/CHECKPOINT.md": 80}
fails, warns = [], []

for rel in REQUIRED:
    if not (ROOT / rel).exists():
        fails.append(f"missing: {rel}")
for rel in MUST_FILL:
    p = ROOT / rel
    if not p.exists():
        fails.append(f"missing: {rel}")
    else:
        text = p.read_text(encoding="utf-8", errors="replace")
        for marker in ("TODO", "TO CONFIRM"):
            if marker in text:
                fails.append(f"'{marker}' left in {rel}")
for rel, limit in LIMITS.items():
    p = ROOT / rel
    if p.exists() and len(p.read_text(encoding="utf-8", errors="replace").splitlines()) > limit:
        warns.append(f"{rel} is over {limit} lines; condense it so a new agent can read it")

try:
    protected = json.loads((ROOT / ".project.json").read_text(encoding="utf-8"))["layout"]["protected_paths"]
except (OSError, KeyError, ValueError):
    protected = []
if protected and (ROOT / ".git").exists():
    try:
        out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True,
                             text=True, check=True).stdout.splitlines()
        for line in out:
            path = line[3:].strip().strip('"')
            if any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in protected):
                fails.append(f"change under protected path: {path}")
    except (OSError, subprocess.CalledProcessError):
        warns.append("could not read Git status; protected paths not checked")

for w in warns:
    print("WARN ", w)
for f in fails:
    print("FAIL ", f)
print("OK" if not fails else f"{len(fails)} problem(s)")
sys.exit(1 if fails else 0)
