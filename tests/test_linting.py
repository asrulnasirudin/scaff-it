"""Installation consent, preservation, detection, and failure regressions."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from scaffolder import cli  # noqa: E402
from scaffolder.tooling import linting  # noqa: E402


class LintSetup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_python_preserves_config_and_is_idempotent(self):
        (self.root / "ruff.toml").write_text('line-length = 100\n')
        plan = linting.plan(self.root)
        self.assertNotIn("ruff.toml", plan.changes)
        linting.apply(plan)
        self.assertFalse(linting.plan(self.root).changes)

    def test_node_keeps_existing_versions_scripts_and_configuration(self):
        original = {"scripts": {"lint": "eslint src", "build": "custom"}, "devDependencies": {"eslint": "^10", "plugin": "1"}}
        (self.root / "package.json").write_text(json.dumps(original))
        (self.root / "eslint.config.mjs").write_text("export default [];\n")
        plan = linting.plan(self.root)
        self.assertNotIn("package.json", plan.changes)
        self.assertNotIn("eslint.config.mjs", plan.changes)

    def test_node_adds_only_missing_lint_fields(self):
        original = {"scripts": {"build": "custom"}, "dependencies": {"typescript": "5.8.0"}}
        (self.root / "package.json").write_text(json.dumps(original))
        plan = linting.plan(self.root)
        package = json.loads(plan.changes["package.json"])
        self.assertEqual(package["scripts"]["build"], "custom")
        self.assertEqual(package["dependencies"], original["dependencies"])
        self.assertNotIn("typescript", package["devDependencies"])

    def test_installer_preserves_combined_settings_and_includes_development_tools(self):
        from scaffolder.apply import apply
        from scaffolder.layers import Layer, load_catalog
        from scaffolder.resolve import Choices, resolve
        catalog = load_catalog()
        catalog["feature:format_test"] = Layer("feature", "format_test", "Test formatter", "1", {
            "json_merge": {"package.json": {"scripts": {"format": "example --check"},
                                            "devDependencies": {"example-formatter": "1.0.0"}}}})
        choices = Choices("Demo", "Demo", picks={"category": ["tool"], "platform": ["windows"],
                          "stack": ["node_typescript"], "state": ["new"], "distribution": ["none"],
                          "feature": ["format_test"]}, git=False)
        resolved = resolve(choices, catalog, self.root)
        apply(resolved)
        original = (resolved.root / "package.json").read_text(encoding="utf-8")
        plan = linting.plan(resolved.root)
        self.assertNotIn("package.json", plan.changes)
        linting.apply(plan)
        with patch.object(linting.shutil, "which", return_value="npm"), \
                patch.object(linting.subprocess, "run") as run:
            run.return_value.returncode = 0
            self.assertTrue(linting.install_and_check(plan))
        self.assertEqual(run.call_args_list[0].args[0], ["npm", "install", "--ignore-scripts", "--include=dev"])
        self.assertEqual(run.call_count, 2)
        self.assertEqual((resolved.root / "package.json").read_text(encoding="utf-8"), original)

    def test_unchanged_manifest_and_lockfile_changes_abort_before_writes_or_install(self):
        (self.root / "package.json").write_text(json.dumps({"scripts": {"lint": "eslint ."},
                                                        "devDependencies": {"eslint": "^10"}}))
        (self.root / "eslint.config.mjs").write_text("export default [];\n")
        for name in ("package.json", "package-lock.json", "npm-shrinkwrap.json"):
            with self.subTest(name=name):
                plan = linting.plan(self.root)
                target = self.root / name
                old = target.read_text() if target.exists() else None
                target.write_text('{}')
                with self.assertRaisesRegex(linting.LintError, "changed since preview"):
                    linting.apply(plan)
                with patch.object(linting.subprocess, "run") as run:
                    with self.assertRaisesRegex(linting.LintError, "changed since setup preview"):
                        linting.install_and_check(plan)
                run.assert_not_called()
                self.assertFalse((self.root / ".gitignore").exists())
                if old is None:
                    target.unlink()
                else:
                    target.write_text(old)

    def test_manifest_changed_after_apply_prevents_installation(self):
        (self.root / "package.json").write_text('{}')
        plan = linting.plan(self.root)
        linting.apply(plan)
        (self.root / "package.json").write_text('{"scripts": {"lint": "changed"}}')
        with patch.object(linting.subprocess, "run") as run:
            with self.assertRaisesRegex(linting.LintError, "package.json changed"):
                linting.install_and_check(plan)
        run.assert_not_called()

    def test_ambiguous_or_unsupported_setup_refuses_changes(self):
        for stack in (None, "godot"):
            with self.assertRaises(linting.LintError):
                linting.plan(self.root, stack)
        (self.root / ".flake8").write_text("[flake8]\n")
        with self.assertRaises(linting.LintError):
            linting.plan(self.root, "python")

    def test_changed_file_aborts_before_any_writes(self):
        plan = linting.plan(self.root, "python")
        (self.root / ".gitignore").write_text("changed\n")
        with self.assertRaises(linting.LintError):
            linting.apply(plan)
        self.assertFalse((self.root / "ruff.toml").exists())

    def test_link_refusal(self):
        with patch.object(linting, "linked_ancestor", return_value=self.root):
            with self.assertRaises(linting.LintError):
                linting.plan(self.root, "python")

    def test_dry_run_never_installs_or_writes(self):
        with patch.object(linting, "install_and_check") as install:
            cli.main(["--setup-lint", str(self.root), "--stack", "python", "--install-tools", "--dry-run"])
        install.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_yes_does_not_authorize_installation(self):
        with patch.object(linting, "install_and_check") as install:
            cli.main(["--setup-lint", str(self.root), "--stack", "python", "--yes"])
        install.assert_not_called()
        self.assertTrue((self.root / "ruff.toml").exists())

    def test_declining_setup_leaves_existing_project_untouched(self):
        with patch("builtins.input", return_value="n"), patch.object(linting, "install_and_check") as install:
            cli.main(["--setup-lint", str(self.root), "--stack", "python", "--install-tools"])
        install.assert_not_called()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_separate_interactive_install_consent(self):
        with patch("builtins.input", side_effect=["y", "n"]), patch.object(linting, "install_and_check") as install:
            cli.main(["--setup-lint", str(self.root), "--stack", "python"])
        install.assert_not_called()
        self.assertTrue((self.root / "ruff.toml").exists())

    def test_explicit_install_and_failure_exit(self):
        with patch.object(linting, "install_and_check", return_value=False) as install:
            with self.assertRaises(SystemExit) as error:
                cli.main(["--setup-lint", str(self.root), "--stack", "python", "--yes", "--install-tools"])
        self.assertEqual(error.exception.code, 1)
        install.assert_called_once()
        self.assertTrue((self.root / "ruff.toml").exists())

    def test_install_stops_after_failed_environment_creation(self):
        plan = linting.plan(self.root, "python")
        linting.apply(plan)
        with patch.object(linting.subprocess, "run") as run:
            run.return_value.returncode = 1
            self.assertFalse(linting.install_and_check(plan))
        self.assertEqual(run.call_count, 1)
        self.assertIn("venv", run.call_args.args[0])

    def test_non_npm_and_legacy_configs_are_not_replaced(self):
        (self.root / "package.json").write_text('{}')
        for name in ("pnpm-lock.yaml", ".eslintrc.json"):
            file = self.root / name
            file.write_text('{}')
            with self.assertRaises(linting.LintError):
                linting.plan(self.root)
            file.unlink()

    def test_new_project_yes_configures_without_installing(self):
        args = ["Demo", "--category", "tool", "--platform", "windows", "--stack", "python", "--ai", "none",
                "--distribution", "none", "--features", "none", "--no-git", "--out", str(self.root), "--yes"]
        with patch.object(linting, "install_and_check") as install:
            cli.main(args)
        install.assert_not_called()
        self.assertTrue((self.root / "Demo" / "ruff.toml").exists())

    def test_new_project_explicit_install(self):
        args = ["Demo", "--category", "tool", "--platform", "windows", "--stack", "python", "--ai", "none",
                "--distribution", "none", "--features", "none", "--no-git", "--out", str(self.root), "--yes", "--install-tools"]
        with patch.object(linting, "install_and_check", return_value=True) as install:
            cli.main(args)
        install.assert_called_once()
