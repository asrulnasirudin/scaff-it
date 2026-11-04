"""Security regressions use synthetic values and disposable destinations only."""
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from scaffolder import apply as ap  # noqa: E402

SPEC = importlib.util.spec_from_file_location("safety_under_test", ROOT / ".agent/safety_check.py")
SAFETY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SAFETY)


class SecurityRegression(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def scan(self, files):
        with patch.object(SAFETY, "candidate_files", return_value=(files, "walk")):
            return SAFETY.scan(self.root)[0]

    def test_example_file_content_is_scanned_and_values_are_redacted(self):
        value = "github_pat_" + "Z" * 60
        (self.root / ".env.example").write_text("SERVICE_TOKEN=" + value)
        findings = self.scan([".env.example"])
        self.assertTrue(any(f[1] == "fine_grained_code_host_token" for f in findings))
        self.assertFalse(any(f[1] == "secret_file_tracked" for f in findings))
        self.assertNotIn(value, json.dumps(findings))

    def test_large_and_non_utf8_files_are_not_silently_skipped(self):
        (self.root / "large.txt").write_bytes(b"\xff\n" + b"padding\n" * 150000 + b"sk-proj-" + b"Z" * 48)
        self.assertTrue(any(f[1] == "service_api_token" for f in self.scan(["large.txt"])))

    def test_unquoted_and_json_credentials_and_url_passwords(self):
        value = "synthetic-" + "Z" * 24
        lines = ["API_KEY=" + value, json.dumps({"password": value}), "https://user:" + value + "@host.invalid",
                 "SERVICE_API_KEY=" + value, "AWS_SECRET_ACCESS_KEY=" + value]
        self.assertEqual({f[3] for f in SAFETY.content_findings(lines, "config.txt")}, {1, 2, 3, 4, 5})

    def test_provider_tokens_do_not_get_placeholder_exemptions(self):
        token = "ghp_" + "example" + "Z" * 36
        self.assertTrue(SAFETY.content_findings([token], "config.txt"))
        self.assertFalse(SAFETY.content_findings(['token = "your-token-here"'], "config.txt"))

    def test_linked_candidates_are_rejected_without_reading(self):
        (self.root / "candidate.txt").write_text("unchanged")
        policy = SAFETY.load_policy(self.root)
        with patch.object(SAFETY, "load_policy", return_value=policy), \
                patch.object(SAFETY, "linked_path", return_value=True), \
                patch.object(Path, "open", side_effect=AssertionError):
            self.assertIn(("FAIL", "linked_candidate", "candidate.txt", None), self.scan(["candidate.txt"]))

    def test_exclusive_create_preserves_existing_file(self):
        target = self.root / "keep.txt"
        target.write_text("existing content")
        with self.assertRaises(FileExistsError):
            ap._write_file(target, "replacement")
        self.assertEqual(target.read_text(), "existing content")

    @unittest.skipUnless(shutil.which("git"), "Git unavailable")
    def test_staged_secret_is_found_after_working_copy_is_cleaned(self):
        subprocess.run(["git", "init", str(self.root)], check=True, capture_output=True)
        target = self.root / "config.txt"
        target.write_text("ghp_" + "Z" * 40)
        subprocess.run(["git", "-C", str(self.root), "add", "config.txt"], check=True, capture_output=True)
        target.write_text("safe working copy")
        findings = SAFETY.scan(self.root)[0]
        self.assertTrue(any(f[1] == "code_host_token" and f[2] == "config.txt (index)" for f in findings))

    def test_rollback_keeps_files_under_replaced_link_or_junction(self):
        target = self.root / "keep.txt"
        target.write_text("unchanged")
        journal = ap.Journal()
        journal.files = [("keep.txt", ap.sha("unchanged"))]
        journal.dirs = ["nested"]
        journal.root_created = True
        with patch.object(ap, "linked_ancestor", return_value=self.root), patch.object(Path, "unlink", side_effect=AssertionError):
            removed, kept = ap.rollback(SimpleNamespace(root=self.root), journal)
        self.assertEqual(removed, [])
        self.assertIn("keep.txt", kept)
        self.assertIn("nested/", kept)
        self.assertEqual(target.read_text(), "unchanged")


if __name__ == "__main__":
    unittest.main()
