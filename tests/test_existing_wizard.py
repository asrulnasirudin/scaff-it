"""Exercise folder selection and preserve the existing setup consent boundary."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from scaffolder.tooling import existing  # noqa: E402


class ExistingWizard(unittest.TestCase):
    def test_cancel_does_not_start_setup(self):
        for answers, folder in ((["0"], None), (["1"], "")):
            with self.subTest(answers=answers), patch("builtins.input", side_effect=answers), \
                    patch.object(existing, "browse_folder", return_value=folder), \
                    patch.object(existing.cli, "main") as run, patch("builtins.print"):
                existing.main()
                run.assert_not_called()

    def test_selected_folder_reuses_interactive_consent(self):
        with tempfile.TemporaryDirectory(prefix="wizard project ") as folder:
            for stack, extra in (("1", []), ("2", ["--stack", "python"]),
                                 ("3", ["--stack", "node_typescript"])):
                with self.subTest(stack=stack), patch("builtins.input", side_effect=["1", stack]), \
                        patch.object(existing, "browse_folder", return_value=folder), \
                        patch.object(existing.cli, "main") as run, patch("builtins.print"):
                    existing.main()
                    run.assert_called_once_with(["--setup-lint", str(Path(folder).absolute()), *extra])

    def test_browser_unavailable_allows_quoted_path(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("builtins.input", side_effect=["1", f'"{folder}"', "2"]), \
                patch.object(existing, "browse_folder", return_value=None), \
                patch.object(existing.cli, "main") as run, patch("builtins.print"):
            existing.main()
            run.assert_called_once_with(["--setup-lint", str(Path(folder).absolute()), "--stack", "python"])

    def test_real_setup_can_be_declined_without_writes(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("builtins.input", side_effect=["2", folder, "2", "n"]), patch("builtins.print"):
            existing.main()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_invalid_folder_reprompts_and_eof_exits(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("builtins.input", side_effect=["2", str(Path(folder) / "missing"), "0"]), \
                patch.object(existing.cli, "main") as run, patch("builtins.print"):
            existing.main()
            run.assert_not_called()
        with patch("builtins.input", side_effect=EOFError), \
                patch.object(existing.cli, "main") as run, patch("builtins.print"):
            existing.main()
            run.assert_not_called()
