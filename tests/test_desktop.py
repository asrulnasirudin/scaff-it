"""Portable runtime dispatch and bundled lint checks must not reexecute the bootloader."""
import sys
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scaffolder import desktop, cli  # noqa: E402
from scaffolder.tooling import linting, launcher  # noqa: E402


class PortableRuntime(unittest.TestCase):
    def test_flags_dispatch_to_cli_without_close_prompt(self):
        with patch.object(cli, "main") as run, patch("builtins.input") as prompt:
            desktop.main(["--help"])
            run.assert_called_once_with(["--help"])
            prompt.assert_not_called()

    def test_frozen_interactive_results_wait_before_closing(self):
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys.stdin, "isatty", return_value=True), \
                patch.object(launcher, "main"), patch("builtins.input") as prompt:
            desktop.main([])
            prompt.assert_called_once()

    def test_bundled_python_check_uses_native_ruff_without_venv_or_download(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tool = root / "runtime/tools/ruff.exe"
            tool.parent.mkdir(parents=True)
            tool.write_bytes(b"test-only placeholder")
            with patch.object(sys, "frozen", True, create=True), \
                    patch.object(sys, "_MEIPASS", str(tool.parent.parent), create=True):
                plan = linting.plan(root, "python")
                linting.apply(plan)
                with patch.object(linting.subprocess, "run") as run:
                    run.return_value.returncode = 0
                    self.assertTrue(linting.install_and_check(plan))
                    run.assert_called_once_with([str(tool), "check", ".", "--extend-exclude", ".venv-lint"],
                                                cwd=root, check=False)
                self.assertFalse((root / ".venv-lint").exists())

    def test_missing_bundled_ruff_refuses_without_falling_back_to_bootloader(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sys, "frozen", True, create=True), \
                patch.object(sys, "_MEIPASS", folder, create=True):
            plan = linting.plan(folder, "python")
            linting.apply(plan)
            with patch.object(linting.subprocess, "run") as run, self.assertRaises(linting.LintError):
                linting.install_and_check(plan)
            run.assert_not_called()

    def test_interactive_error_is_visible_before_close_prompt(self):
        output = io.StringIO()
        with patch.object(sys, "frozen", True, create=True), \
                patch.object(sys.stdin, "isatty", return_value=True), \
                patch.object(launcher, "main", side_effect=SystemExit("Useful error")), \
                patch("builtins.input", side_effect=lambda _: self.assertIn("Useful error", output.getvalue())), \
                redirect_stdout(output), self.assertRaises(SystemExit) as error:
            desktop.main([])
        self.assertEqual(error.exception.code, 1)
