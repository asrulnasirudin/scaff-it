"""Changelog generation, release preservation, CLI consent and refusal checks."""
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from scaffolder import changelog  # noqa: E402
from scaffolder.layers import load_catalog  # noqa: E402
from scaffolder.resolve import Choices, resolve  # noqa: E402


class Changelogs(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "CHANGELOG.md"
        self.header = (SRC / "templates/v2/changelog.md").read_bytes()

    def pending(self, suffix=b"", newline=b"\n"):
        content = self.header + b"\n### Added\n\n- New feature.\n\n### Fixed\n\n- A bug.\n\n" + suffix
        self.path.write_bytes(content.replace(b"\n", newline))

    def cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(SRC / "new_project.py"), *args],
                              input=stdin, text=True, capture_output=True)

    def test_new_projects_include_template_guidance_and_managed_hash(self):
        for ai in ([], ["codex"]):
            with self.subTest(ai=ai):
                selected = Choices("Demo", "Demo", picks={"category": ["tool"], "platform": ["windows"],
                                   "state": ["new"], "distribution": ["none"], "ai": ai}, git=False)
                result = resolve(selected, load_catalog(), self.root)
                self.assertEqual(result.files["CHANGELOG.md"].encode(), self.header)
                self.assertNotIn("## [1.", result.files["CHANGELOG.md"])
                for term in ("CHANGELOG.md", "Unreleased", "Semantic Versioning", "Security"):
                    self.assertIn(term, result.files["AGENTS.md"])
                record = next(r for r in result.descriptor["scaffold"]["managed_files"]
                              if r["path"] == "CHANGELOG.md")
                self.assertEqual(record["sha256"], hashlib.sha256(self.header).hexdigest())
                self.assertFalse(result.root.exists())

    def test_initialize_and_repeat_preserve_custom_content(self):
        result = changelog.plan(self.root)
        self.assertFalse(self.path.exists())
        changelog.apply(result)
        self.assertEqual(self.path.read_bytes(), self.header)
        self.pending()
        before = self.path.read_bytes()
        changelog.apply(changelog.plan(self.root))
        self.assertEqual(self.path.read_bytes(), before)

    def test_release_moves_changes_and_preserves_old_history_and_links(self):
        history = (b"## [1.0.0] - 2025-01-01\n\n### Added\n\n- Initial release.\n\n"
                   b"[Unreleased]: https://example.com/compare/main\n[1.0.0]: https://example.com/v1\n")
        self.pending(history)
        result = changelog.plan(self.root, "1.1.0", "2026-11-02")
        self.assertNotIn(b"## [1.1.0]", self.path.read_bytes())
        changelog.apply(result)
        content = self.path.read_bytes()
        self.assertIn(b"## [Unreleased]\n\n## [1.1.0] - 2026-11-02\n\n### Added", content)
        self.assertIn(b"### Fixed\n\n- A bug.", content)
        self.assertTrue(content.endswith(history))

    def test_crlf_and_reference_definitions_survive_first_release(self):
        self.pending(b"[Unreleased]: https://example.com/main\n", newline=b"\r\n")
        result = changelog.plan(self.root, "0.1.0", "2026-11-02")
        self.assertNotIn(b"\n", result.after.replace(b"\r\n", b""))
        self.assertTrue(result.after.endswith(b"[Unreleased]: https://example.com/main\r\n"))

    def test_default_date(self):
        self.pending()
        with patch.object(changelog, "date") as clock:
            from datetime import date
            clock.today.return_value = date(2026, 11, 2)
            clock.fromisoformat = date.fromisoformat
            self.assertIn(b" - 2026-11-02", changelog.plan(self.root, "0.1.0").after)

    def test_missing_empty_and_headings_only_cannot_release(self):
        for content in (None, self.header, self.header + b"\n### Added\n\n### Fixed\n"):
            with self.subTest(content=content):
                if content is not None:
                    self.path.write_bytes(content)
                with self.assertRaises(changelog.ChangelogError):
                    changelog.plan(self.root, "1.0.0")

    def test_invalid_versions_and_dates_do_not_write(self):
        self.pending()
        before = self.path.read_bytes()
        for version in ("", "1.0", "v1.0.0", "01.0.0", "1.0.0-01", "1.0.0+", "../x"):
            with self.subTest(version=version), self.assertRaises(changelog.ChangelogError):
                changelog.plan(self.root, version)
        for stamp in ("", "2026-02-30", "20261102", "2026-1-2"):
            with self.subTest(stamp=stamp), self.assertRaises(changelog.ChangelogError):
                changelog.plan(self.root, "1.0.0", stamp)
        self.assertEqual(self.path.read_bytes(), before)

    def test_semver_order_duplicates_prereleases_and_metadata(self):
        self.pending(b"## [1.0.0-rc.2+build.1] - 2026-11-01\n\n- Prior.\n")
        for version in ("0.9.9", "1.0.0-rc.1", "1.0.0-rc.2+build.2"):
            with self.subTest(version=version), self.assertRaises(changelog.ChangelogError):
                changelog.plan(self.root, version)
        for version in ("1.0.0-rc.10", "1.0.0", "1.1.0-beta.0+build.02"):
            with self.subTest(version=version):
                self.assertIn(version.encode(), changelog.plan(self.root, version).after)

    def test_ambiguous_structure_refused(self):
        for content in (b"# Custom\n", self.header + b"\n## [Unreleased]\n",
                        self.header + b"\n- Change.\n\n## Notes\n"):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(changelog.ChangelogError):
                    changelog.plan(self.root, "1.0.0")

    def test_stale_preview_and_linked_paths_refused(self):
        result = changelog.plan(self.root)
        self.path.write_bytes(b"Existing content")
        with self.assertRaises(changelog.ChangelogError):
            changelog.apply(result)
        self.assertEqual(self.path.read_bytes(), b"Existing content")
        with patch.object(changelog, "linked_ancestor", return_value=self.path):
            with self.assertRaises(changelog.ChangelogError):
                changelog.plan(self.root)

    def test_missing_project_and_directory_target_refused(self):
        with self.assertRaises(changelog.ChangelogError):
            changelog.plan(self.root / "missing")
        self.path.mkdir()
        with self.assertRaises(changelog.ChangelogError):
            changelog.plan(self.root)

    def test_cli_preview_cancel_initialize_and_release(self):
        for args, stdin in ((("--dry-run",), ""), ((), "n\n")):
            result = self.cli("--changelog", str(self.root), *args, stdin=stdin)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(self.path.exists())
        result = self.cli("--changelog", str(self.root), "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.pending()
        before = self.path.read_bytes()
        release = ("--changelog", str(self.root), "--release", "1.0.0", "--release-date", "2026-11-02")
        result = self.cli(*release, "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.path.read_bytes(), before)
        result = self.cli(*release, "--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"## [1.0.0] - 2026-11-02", self.path.read_bytes())
        result = self.cli(*release, "--yes")
        self.assertNotEqual(result.returncode, 0)

    def test_cli_requires_context_and_rejects_conflicting_modes(self):
        for args in (("--release", "1.0.0"), ("--release-date", "2026-11-02"),
                     ("--changelog", str(self.root), "--release-date", "2026-11-02"),
                     ("--changelog", str(self.root), "--setup-lint", str(self.root)),
                     ("--changelog", str(self.root), "--install-tools")):
            with self.subTest(args=args):
                self.assertNotEqual(self.cli(*args).returncode, 0)
                self.assertFalse(self.path.exists())


if __name__ == "__main__":
    unittest.main()
