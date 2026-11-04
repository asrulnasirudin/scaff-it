#!/usr/bin/env python3
"""Repository safety check. Run before your first commit and before sharing a repository:

    python .agent/safety_check.py

Looks at the files a `git add -A` would stage (all files when Git is not used) and reports:
  FAIL  secret-looking files or content, or local-only material that is tracked
  WARN  files named like credentials, files over the size limit, watched file types
It only reads. It never deletes, moves or rewrites anything, and it never prints a secret value:
findings show the file, line number and rule name only. Standard library only; no network.
Policy comes from .project.json ("security"). Exit code 1 if any FAIL.
"""
import fnmatch
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

PLACEHOLDER = re.compile(r"(?i)(your|example|placeholder|changeme|change-me|dummy|sample|xxx|<|\.\.\.|\$\{|%\()")
CONTENT_RULES = [
    ("private_key_block", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("cloud_access_key_id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("code_host_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("fine_grained_code_host_token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("service_api_token", re.compile(r"\b(?:sk-(?:proj-|ant-api\d+-)?)[A-Za-z0-9_-]{32,}\b")),
    ("chat_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("hardcoded_credential", re.compile(
        r"(?i)(?<![/\\\w])(?:[a-z]+[_-])*(?:api[_-]?key|secret(?:[_-]access[_-]key)?|(?:access[_-])?token|passwd|password)\b"
        r"[\"']?\s*[:=]\s*(?:[\"']([^\"'\s]{12,})[\"']|([A-Za-z0-9_./+=:@-]{12,})(?=\s*(?:$|#)))")),
    ("credential_in_url", re.compile(r"[a-z][a-z0-9+.-]*://[^\s/:@]+:([^\s/@]{4,})@", re.I)),
]


def content_findings(lines, rel):
    """Scan all lines, including examples; never return credential values."""
    findings = []
    for n, line in enumerate(lines, 1):
        for rule, rx in CONTENT_RULES:
            for match in rx.finditer(line):
                value = next((g for g in match.groups() if g is not None), match.group(0))
                if rule in ("hardcoded_credential", "credential_in_url") and PLACEHOLDER.search(value):
                    continue
                findings.append(("FAIL", rule, rel, n))
    return findings


def linked_path(path):
    """Do not follow symlinks or Windows junctions while inspecting candidates."""
    for part in (path, *path.parents):
        try:
            info = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            return True
    return False


def load_policy(root):
    try:
        policy_path = root / ".project.json"
        sec = {} if linked_path(policy_path) else json.loads(policy_path.read_text(encoding="utf-8")).get("security", {})
    except (OSError, ValueError):
        sec = {}
    return {
        "watch": sec.get("watch_patterns", ["credentials.*", "secrets.*"]),
        "secret": sec.get("secret_patterns", [".env", ".env.*", "*.pem", "*.key", "*.pfx", "*.p12"]),
        "large_mb": sec.get("large_file_warn_mb", 5),
        "local": [p.strip("/") for p in sec.get("local_only", []) if p.endswith("/")],
    }


def candidate_files(root):
    """Relative paths git would stage; falls back to walking the folder when Git is unavailable."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=root, capture_output=True, check=True).stdout
        names = [n.decode("utf-8", "replace") for n in out.split(b"\0") if n]
        return sorted(set(names)), "git"
    except (OSError, subprocess.CalledProcessError):
        names = [p.relative_to(root).as_posix() for p in root.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(root).parts]
        return sorted(names), "walk"


def matches(name, patterns):
    base = name.rsplit("/", 1)[-1]
    return any(fnmatch.fnmatch(base.lower(), p.lower()) or fnmatch.fnmatch(name.lower(), p.lower())
               for p in patterns if not p.startswith("!"))


def staged_findings(root, policy):
    """Check staged changes too: a cleaned working copy may hide a staged credential."""
    findings = []
    try:
        names = subprocess.run(["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMRTU"],
                               cwd=root, capture_output=True, check=True).stdout
        for raw in names.split(b"\0"):
            if not raw:
                continue
            rel = raw.decode("utf-8", "replace")
            label = rel + " (index)"
            if matches(rel, policy["secret"]) and rel.rsplit("/", 1)[-1] != ".env.example":
                findings.append(("FAIL", "secret_file_tracked", label, None))
            for loc in policy["local"]:
                if rel.startswith(loc + "/") and rel != loc + "/README.md":
                    findings.append(("FAIL", "local_only_tracked", label, None))
            blob = subprocess.run(["git", "show", ":" + rel], cwd=root, capture_output=True, check=True).stdout
            findings.extend(content_findings(blob.decode("utf-8", "replace").splitlines(), label))
    except (OSError, subprocess.CalledProcessError):
        findings.append(("FAIL", "cannot_scan_index", "(index)", None))
    return findings


def scan(root):
    """Return (findings, mode). Each finding: (level, rule, path, line_or_None)."""
    root = Path(root)
    policy = load_policy(root)
    files, mode = candidate_files(root)
    findings = []
    for rel in files:
        path = root / rel
        if linked_path(path):
            findings.append(("FAIL", "linked_candidate", rel, None))
            continue
        if not path.is_file():
            continue
        exempt = rel.rsplit("/", 1)[-1] == ".env.example"
        if matches(rel, policy["secret"]) and not exempt:
            findings.append(("FAIL", "secret_file_tracked", rel, None))
        for loc in policy["local"]:
            if rel.startswith(loc + "/") and rel != loc + "/README.md":
                findings.append(("FAIL", "local_only_tracked", rel, None))
        if matches(rel, policy["watch"]):
            findings.append(("WARN", "watched_file_name", rel, None))
        try:
            size = path.stat().st_size
        except OSError:
            findings.append(("FAIL", "unreadable_candidate", rel, None))
            continue
        if size > policy["large_mb"] * 1024 * 1024:
            findings.append(("WARN", f"large_file_over_{policy['large_mb']}MB", rel, None))
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                findings.extend(content_findings(stream, rel))
        except OSError:
            findings.append(("FAIL", "unreadable_candidate", rel, None))
    if mode == "git":
        findings.extend(staged_findings(root, policy))
    return findings, mode


def main(argv=None):
    root = Path(__file__).resolve().parent.parent
    findings, mode = scan(root)
    if mode == "walk":
        print("NOTE  Git not available here: scanned every file, ignore rules not applied.")
    for level, rule, rel, line in findings:
        print(f"{level:<5} {rule}  {rel}" + (f":{line}" if line else ""))
    fails = sum(1 for f in findings if f[0] == "FAIL")
    warns = len(findings) - fails
    print(f"{'OK' if not fails else 'NOT SAFE TO COMMIT'}: {fails} failure(s), {warns} warning(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
