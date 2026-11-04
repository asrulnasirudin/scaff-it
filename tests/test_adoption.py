"""Existing-project scaffolding: preservation, metadata, previews and write boundaries."""
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))
from scaffolder import adoption  # noqa: E402
from scaffolder.apply import ApplyError  # noqa: E402
from scaffolder.layers import load_catalog  # noqa: E402
from scaffolder.resolve import Choices, resolve  # noqa: E402
from scaffolder.tooling import launcher  # noqa: E402


class ExistingScaffolds(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "Existing Project"
        self.root.mkdir()

    def resolved(self):
        choices = Choices(self.root.name, self.root.name, picks={
            "category": ["tool"], "platform": ["windows"], "state": ["existing"],
            "stack": ["python"], "ai": ["codex"], "distribution": ["none"]}, git=False)
        return resolve(choices, adoption.existing_catalog(load_catalog()), self.root.parent)

    def cli(self, *args, stdin=""):
        return subprocess.run([sys.executable, str(SRC / "new_project.py"),
                               "--scaffold-existing", str(self.root), "--category", "tool",
                               "--platform", "windows", "--stack", "python", "--target", "none",
                               "--ai", "codex", "--distribution", "none", "--features", "none",
                               "--description", "Existing tool", *args],
                              input=stdin, text=True, capture_output=True)

    def test_preserves_binary_readme_source_ignore_and_history(self):
        originals = {"README.md": b"Original\r\n\xff", "src/app.py": b"print('hello')\n",
                     ".gitignore": b"custom/\r\n", ".git/HEAD": b"ref: refs/heads/work\n",
                     ".agent/MEMORY.md": b"Existing memory", ".env": b"placeholder-only"}
        for rel, data in originals.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        additions = adoption.plan(self.resolved())
        adoption.apply(additions)
        for rel, data in originals.items():
            self.assertEqual((self.root / rel).read_bytes(), data)
        for rel in ("AGENTS.md", "PROJECT_SPEC.md", "CHANGELOG.md", ".agent/CHECKPOINT.md",
                    ".agent/check.py", "docs/user/README.md", "ruff.toml"):
            self.assertTrue((self.root / rel).is_file(), rel)
        checkpoint = (self.root / ".agent/CHECKPOINT.md").read_text()
        self.assertNotIn("No application code exists", checkpoint)
        self.assertIn("not been assessed", checkpoint)
        self.assertIn("state: Existing project", (self.root / "AGENTS.md").read_text())

    def test_descriptor_tracks_only_additions_with_final_hashes(self):
        (self.root / "README.md").write_bytes(b"Keep")
        additions = adoption.plan(self.resolved())
        adoption.apply(additions)
        descriptor = json.loads((self.root / ".project.json").read_text())
        self.assertEqual(descriptor["state"], "existing")
        self.assertEqual(descriptor["scaffold"]["mode"], "add_missing")
        self.assertIn("README.md", descriptor["scaffold"]["preserved_files"])
        managed = descriptor["scaffold"]["managed_files"]
        self.assertNotIn("README.md", [entry["path"] for entry in managed])
        for entry in managed:
            self.assertEqual(entry["sha256"], hashlib.sha256((self.root / entry["path"]).read_bytes()).hexdigest())

    def test_existing_descriptor_is_opaque_and_repeat_run_adds_nothing(self):
        descriptor = b'{"schema_version":1,"custom":"keep"}\r\n'
        (self.root / ".project.json").write_bytes(descriptor)
        adoption.apply(adoption.plan(self.resolved()))
        self.assertEqual((self.root / ".project.json").read_bytes(), descriptor)
        self.assertEqual(adoption.plan(self.resolved()).files, {})

    def test_stale_preview_refuses_before_writing(self):
        additions = adoption.plan(self.resolved())
        (self.root / "AGENTS.md").write_text("Someone else's instructions")
        with self.assertRaises(ApplyError) as caught:
            adoption.apply(additions)
        self.assertEqual(caught.exception.journal.files, [])
        self.assertFalse((self.root / "PROJECT_SPEC.md").exists())
        self.assertEqual((self.root / "AGENTS.md").read_text(), "Someone else's instructions")

    def test_existing_file_changes_are_kept_without_reading_content(self):
        (self.root / "README.md").write_bytes(b"before")
        additions = adoption.plan(self.resolved())
        (self.root / "README.md").write_bytes(b"after")
        adoption.apply(additions)
        self.assertEqual((self.root / "README.md").read_bytes(), b"after")

    def test_file_folder_collisions_are_refused(self):
        (self.root / "docs").write_text("Not a directory")
        with self.assertRaises(ValueError):
            adoption.plan(self.resolved())
        (self.root / "docs").unlink()
        (self.root / "README.md").mkdir()
        with self.assertRaises(ValueError):
            adoption.plan(self.resolved())

    def test_case_collision_is_refused(self):
        (self.root / "readme.md").write_text("Keep")
        with self.assertRaisesRegex(ValueError, "letter case"):
            adoption.plan(self.resolved())

    def test_link_on_planned_path_is_refused(self):
        real = adoption.pathsafe.is_link
        with patch.object(adoption.pathsafe, "is_link", side_effect=lambda p: p.name == "docs" or real(p)):
            with self.assertRaisesRegex(ValueError, "link"):
                adoption.plan(self.resolved())

    def test_partial_failure_reports_created_files_without_touching_old_files(self):
        (self.root / "README.md").write_text("Keep")
        additions = adoption.plan(self.resolved())
        original = Path.open

        def fail(path, mode="r", *args, **kwargs):
            if mode == "x" and path.name == "CHANGELOG.md":
                raise OSError("Simulated write failure")
            return original(path, mode, *args, **kwargs)

        with patch.object(Path, "open", fail), self.assertRaises(ApplyError) as caught:
            adoption.apply(additions)
        self.assertTrue(caught.exception.journal.files)
        self.assertEqual((self.root / "README.md").read_text(), "Keep")
        self.assertFalse((self.root / ".project.json").exists())

    def test_cli_dry_run_cancel_and_apply(self):
        for args, stdin in ((("--dry-run",), ""), ((), "n\n")):
            result = self.cli(*args, stdin=stdin)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(self.root.iterdir()), [])
        result = self.cli("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((self.root / ".agent/CHECKPOINT.md").exists())
        self.assertFalse((self.root / ".git").exists())
        self.assertFalse((self.root / ".venv-lint").exists())

    def test_cli_rejects_install_and_git_flags(self):
        for flag in ("--git", "--first-commit", "--install-tools"):
            result = self.cli(flag)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(list(self.root.iterdir()), [])

    def test_launcher_routes_to_full_scaffold_with_folder_picker(self):
        with patch("builtins.input", side_effect=["1", "1"]), \
                patch.object(launcher, "browse_folder", return_value=str(self.root)), \
                patch.object(launcher.cli, "main") as run, redirect_stdout(io.StringIO()):
            launcher.main()
            run.assert_called_once_with(["--scaffold-existing", str(self.root)])

    def test_launcher_new_project_and_folder_cancel(self):
        with patch("builtins.input", side_effect=["2", "2", str(self.root)]), \
                patch.object(launcher.cli, "main") as run, redirect_stdout(io.StringIO()):
            launcher.main()
            run.assert_called_once_with(["--out", str(self.root)])
        with patch("builtins.input", side_effect=["1", "1"]), \
                patch.object(launcher, "browse_folder", return_value=""), \
                patch.object(launcher.cli, "main") as run, redirect_stdout(io.StringIO()):
            launcher.main()
            run.assert_not_called()
