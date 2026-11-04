"""Scenario tests from the New Project brief (numbers refer to its section 15), plus the
preview menu, recovery and the Repository Safety Check."""
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(ROOT))

from scaffolder import apply as ap, cli, gitops  # noqa: E402
from scaffolder.layers import load_catalog  # noqa: E402
from scaffolder.resolve import Choices, resolve  # noqa: E402

NEW = ROOT / "new_project.py"
CATALOG = load_catalog()
GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}
HAS_GIT = gitops.available()


def cli_run(args, stdin="", env=None):
    return subprocess.run([sys.executable, str(NEW), *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", env=env or GIT_ENV)


def git(path, *args):
    return subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, encoding="utf-8")


def snapshot(root):
    return {p.relative_to(root).as_posix(): (None if p.is_dir() else p.read_bytes()) for p in sorted(root.rglob("*"))}


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.tmp = Path(self._t.name).resolve()

    def make(self, name, *extra, stdin=""):
        r = cli_run([name, "--out", str(self.tmp), "--yes", *extra], stdin)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return self.tmp / name

    def descriptor(self, root):
        return json.loads((root / ".project.json").read_text(encoding="utf-8"))


COMMON = ["--no-git"]


class Scenarios(Tmp):
    def test_01_generic_undecided_stack_is_neutral(self):
        root = self.make("Generic", "--category", "generic", "--platform", "windows", "--stack", "undecided",
                         "--ai", "codex", "--distribution", "none", *COMMON)
        d = self.descriptor(root)
        self.assertEqual((d["stack"], d["stack_status"]), ([], "undecided"))
        self.assertFalse((root / "docs" / "developer" / "architecture.md").exists())
        spec = (root / "PROJECT_SPEC.md").read_text(encoding="utf-8")
        self.assertIn("Undecided. TO CONFIRM", spec)
        self.assertIn("ENVIRONMENT PREPARED — IMPLEMENTATION NOT STARTED",
                      (root / ".agent" / "CHECKPOINT.md").read_text(encoding="utf-8"))
        self.assertNotIn("passed", (root / ".agent" / "CHECKPOINT.md").read_text(encoding="utf-8").lower())

    def test_04_adobe_uxp_profile(self):
        root = self.make("Panel", "--category", "extension", "--platform", "windows", "--target", "photoshop@26",
                         "--stack", "adobe_uxp", "--ai", "codex", "--distribution", "ccx_package", *COMMON)
        d = self.descriptor(root)
        self.assertEqual(d["targets"], [{"id": "photoshop", "version": "26"}])
        self.assertEqual(d["distribution"]["type"], "ccx_package")

    def test_05_multiple_agents_share_one_source_of_truth(self):
        root = self.make("Multi", "--category", "generic", "--platform", "windows", "--stack", "none",
                         "--ai", "codex,claude_code,antigravity", "--distribution", "none", *COMMON)
        for f in ("CLAUDE.md", "GEMINI.md", ".agent/CODEX.md", "AGENTS.md"):
            self.assertTrue((root / f).exists(), f)
        self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8").strip(), "@AGENTS.md")
        self.assertIn("AGENTS.md", (root / "GEMINI.md").read_text(encoding="utf-8"))
        self.assertEqual(sorted((root / "PROJECT_SPEC.md").parent.glob("PROJECT_SPEC*.md")), [root / "PROJECT_SPEC.md"])

    def test_06_user_testing_structure_and_privacy(self):
        root = self.make("UT", "--category", "generic", "--platform", "windows", "--stack", "none", "--ai", "none",
                         "--distribution", "none", "--features", "user_testing", *COMMON)
        for d in ("protocols", "findings", "reports"):
            self.assertTrue((root / "research" / "user-testing" / d).is_dir())
        for d in ("recordings", "raw-notes", "participant-data", "consent"):
            self.assertTrue((root / "local" / "user-testing" / d).is_dir())
            self.assertFalse((root / "local" / "user-testing" / d / ".gitkeep").exists())
        ign = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn("/local/*", ign)
        self.assertIn("!/local/README.md", ign)
        d = self.descriptor(root)
        self.assertTrue(d["features"]["user_testing"])
        self.assertFalse(d["features"]["local_assets"])
        self.assertIn("local/", d["security"]["local_only"])
        if HAS_GIT:
            git(root, "init", "-q")
            (root / "local" / "user-testing" / "participant-data" / "p1.txt").write_text("name", encoding="utf-8")
            (root / "research" / "user-testing" / "findings" / "f1.md").write_text("sanitized", encoding="utf-8")
            status = git(root, "status", "--porcelain", "-uall").stdout
            self.assertNotIn("participant-data", status)
            self.assertIn("findings/f1.md", status)
            self.assertIn("local/README.md", status)

    def test_07_local_assets_flagged_not_globally_ignored(self):
        root = self.make("LA", "--category", "creative", "--platform", "windows", "--stack", "none", "--ai", "none",
                         "--distribution", "none", "--features", "local_assets", *COMMON)
        d = self.descriptor(root)
        self.assertIn("*.aep", d["security"]["watch_patterns"])
        ign = (root / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("*.aep", ign)
        self.assertNotIn("*.mp4", ign)
        self.assertTrue((root / "local" / "production-assets").is_dir())
        if HAS_GIT:
            git(root, "init", "-q")
            (root / "local" / "production-assets" / "cut.aep").write_text("x", encoding="utf-8")
            self.assertEqual(git(root, "check-ignore", "local/production-assets/cut.aep").returncode, 0)
            (root / "assets" / "cut.aep").write_text("x", encoding="utf-8")
            self.assertNotEqual(git(root, "check-ignore", "assets/cut.aep").returncode, 0)

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_08_git_init_without_commit_by_default(self):
        r = cli_run(["G", "--out", str(self.tmp), "--yes", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "none", "--distribution", "none", "--features", "none"])
        self.assertEqual(r.returncode, 0, r.stderr)
        root = self.tmp / "G"
        self.assertEqual(git(root, "symbolic-ref", "--short", "HEAD").stdout.strip(), "main")
        self.assertNotEqual(git(root, "rev-parse", "HEAD").returncode, 0, "no commit may exist")
        self.assertEqual(self.descriptor(root)["git"]["commit_policy"], "ask")

    def test_08b_first_commit_is_opt_in_and_needs_identity(self):
        args = ["C", "--out", str(self.tmp), "--yes", "--category", "generic",
                "--platform", "windows", "--stack", "none", "--ai", "none",
                "--distribution", "none", "--features", "none"]
        with patch("builtins.input", return_value=""), \
             patch.object(gitops, "init", return_value=(True, "Git initialized")), \
             patch.object(cli, "_report_safety", return_value=True), \
             patch.object(gitops, "first_commit", return_value=(True, "Commit requested")) as commit:
            cli.main(args)
            commit.assert_not_called()
            cli.main(["C2" if value == "C" else value for value in args] + ["--first-commit"])
            commit.assert_called_once_with(self.tmp / "C2")
        with patch.object(gitops, "has_identity", return_value=False), \
             patch.object(gitops, "_git") as git_command:
            ok, message = gitops.first_commit(self.tmp)
            self.assertFalse(ok)
            self.assertIn("identity", message.replace("user.name / user.email", "identity"))
            git_command.assert_not_called()

    def test_08c_failed_safety_check_blocks_the_commit(self):
        with patch("builtins.input", return_value=""), \
             patch.object(gitops, "init", return_value=(True, "Git initialized")), \
             patch.object(cli, "_report_safety", return_value=False), \
             patch.object(gitops, "first_commit") as commit:
            cli.main(["B", "--out", str(self.tmp), "--yes", "--category", "generic",
                      "--platform", "windows", "--stack", "none", "--ai", "none",
                      "--distribution", "none", "--features", "none", "--first-commit"])
            commit.assert_not_called()

    def test_08d_git_module_only_runs_allowed_commands(self):
        src = (ROOT / "scaffolder" / "gitops.py").read_text(encoding="utf-8")
        for verb in ("push", "remote", "worktree", "branch", "reset", "rebase", "--force", "clean", "checkout"):
            self.assertNotRegex(src.split('"""', 2)[2], rf'"{verb}"', verb)
        with self.assertRaises(ValueError):
            gitops._git(self.tmp, "push")

    def test_08e_git_workflows_recorded_and_explained(self):
        for wf in ("simple", "feature_branches", "parallel_agents"):
            root = self.make(f"W{wf}", "--category", "generic", "--platform", "windows", "--stack", "none",
                             "--ai", "none", "--distribution", "none", "--features", "none", "--git",
                             "--git-workflow", wf)
            self.assertEqual(self.descriptor(root)["git"]["workflow"], wf)
            self.assertIn(f"Workflow: `{wf}`", (root / "AGENTS.md").read_text(encoding="utf-8"))
        r = cli_run(["Bad", "--out", str(self.tmp), "--yes", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "none", "--distribution", "none", "--features", "none",
                     "--git-workflow", "chaos"])
        self.assertEqual(r.returncode, 2)

    def test_09_existing_destination_is_never_touched(self):
        (self.tmp / "Taken").mkdir()
        (self.tmp / "Taken" / "mine.txt").write_text("precious", encoding="utf-8")
        before = snapshot(self.tmp)
        r = cli_run(["Taken", "--out", str(self.tmp), "--yes", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "none", "--distribution", "none", "--features", "none", *COMMON])
        self.assertEqual(r.returncode, 2)
        self.assertIn("already contains files", r.stderr)
        self.assertEqual(snapshot(self.tmp), before)

    def test_10_dry_run_writes_nothing(self):
        out = self.tmp / "does-not-exist-yet"
        r = cli_run(["D", "--out", str(out), "--dry-run", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "codex", "--distribution", "none", "--features", "none", *COMMON])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PROPOSED STRUCTURE", r.stdout)
        self.assertIn("nothing was written", r.stdout)
        self.assertFalse(out.exists())
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_14_repeated_invocation_never_overwrites(self):
        args = ["Rep", "--category", "generic", "--platform", "windows", "--stack", "none", "--ai", "codex",
                "--distribution", "none", "--features", "none", *COMMON]
        root = self.make("Rep", *args[1:])
        (root / "PROJECT_SPEC.md").write_text("my edits", encoding="utf-8")
        before = snapshot(root)
        r = cli_run([*args, "--out", str(self.tmp), "--yes"])
        self.assertEqual(r.returncode, 2)
        self.assertEqual(snapshot(root), before)

    def test_state_other_than_new_is_rejected_clearly(self):
        r = cli_run(["E", "--out", str(self.tmp), "--yes", "--state", "existing", "--category", "generic",
                     "--platform", "windows", "--stack", "none", "--ai", "none", "--distribution", "none",
                     "--features", "none", *COMMON])
        self.assertEqual(r.returncode, 2)
        self.assertIn("Unknown state 'existing'", r.stderr)
        self.assertEqual(list(self.tmp.iterdir()), [])


class MoreProfiles(unittest.TestCase):
    CASES = [
        dict(category=["generic"]),
        dict(category=["tool"], stack=["python"]),
        dict(category=["app"], platform=["web"], stack=["node_typescript"], distribution=["web_deploy"]),
        dict(category=["app"], platform=["windows"], stack=["tauri"], distribution=["installer"]),
        dict(category=["app"], platform=["windows"], stack=["winui3"], distribution=["installer"]),
        dict(category=["app"], platform=["android"], stack=["android_kotlin"]),
        dict(category=["extension"], target=["photoshop"], stack=["adobe_uxp"], distribution=["ccx_package"]),
        dict(category=["extension"], target=["premiere_pro"], stack=["adobe_uxp"]),
        dict(category=["creative"], feature=["local_assets", "user_testing", "sensitive_config"]),
    ]

    def test_profiles_resolve(self):
        with tempfile.TemporaryDirectory() as t:
            for i, case in enumerate(self.CASES):
                with self.subTest(case=case):
                    case = dict(case)
                    case.setdefault("platform", ["windows"])
                    case.setdefault("state", ["new"])
                    case.setdefault("distribution", ["none"])
                    res = resolve(Choices(name=f"P{i}", folder=f"P{i}", picks=case, versions={}), CATALOG, t)
                    for path, text in res.files.items():
                        self.assertIsNone(re.search(r"@@[A-Z_]+@@", text), path)

    def test_android_keystores_are_secret(self):
        with tempfile.TemporaryDirectory() as t:
            res = resolve(Choices(name="A", folder="A", picks=dict(
                category=["app"], platform=["android"], stack=["android_kotlin"], state=["new"],
                distribution=["none"]), versions={}), CATALOG, t)
            self.assertIn("*.jks", res.files[".gitignore"])


class PreviewMenu(Tmp):
    ANSWERS = "SampleApp\n{out}\nA media library\napp\nwindows\nelectron\ncodex\ninstaller\nn\nn\nn\ny\n\nn\n"

    def run_menu(self, tail):
        return cli_run([], self.ANSWERS.format(out=self.tmp) + tail)

    def test_preview_shows_required_sections(self):
        r = self.run_menu("x\n")
        for text in ("PROJECT:", "Category:", "Stack:", "AI:", "Git:", "Distribution:", "PROPOSED STRUCTURE",
                     "~ build/", "~ dist/", "SECURITY", "Local-only", "[C]reate", "[M]odify", "[B]ack", "[X] Cancel"):
            self.assertIn(text, r.stdout)

    def test_cancel_creates_nothing(self):
        r = self.run_menu("x\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_modify_changes_an_answer_then_creates(self):
        r = self.run_menu("m\n1\nRenamed\nc\n")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue((self.tmp / "Renamed" / ".project.json").exists())
        self.assertFalse((self.tmp / "SampleApp").exists())

    def test_back_reasks_the_last_question(self):
        r = self.run_menu("b\nn\nc\n")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertFalse(json.loads((self.tmp / "SampleApp" / ".project.json").read_text(encoding="utf-8"))["git"]["enabled"])

    def test_invalid_combination_can_be_fixed_in_the_menu(self):
        stdin = ("Bad\n" + str(self.tmp) + "\n\nextension\nwindows\nblender\n\n\n\n\n\n\n\n\n\n")
        r = cli_run([], stdin)
        self.assertNotEqual(r.returncode, 0)  # input runs out: stops cleanly, nothing written
        self.assertEqual(list(self.tmp.iterdir()), [])


class Recovery(Tmp):
    def plan(self, name="Rec"):
        return resolve(Choices(name=name, folder=name, picks=dict(
            category=["generic"], platform=["windows"], ai=["codex"], state=["new"], distribution=["none"]),
            versions={}), CATALOG, self.tmp)

    @staticmethod
    def failing_after(n):
        count = {"n": 0}

        def write(path, text):
            if count["n"] >= n:
                raise OSError("injected failure")
            count["n"] += 1
            ap._write_file(path, text)
        return write

    def test_interrupted_creation_reports_state_and_rerun_completes(self):
        res = self.plan()
        with self.assertRaises(ap.ApplyError) as cm:
            ap.apply(res, _write=self.failing_after(5))
        j = cm.exception.journal
        self.assertEqual(len(j.files), 5)
        self.assertFalse((res.root / ".project.json").exists(), "descriptor is written last")
        self.assertEqual(ap.classify_target(res)[0], "resumable")
        j2 = ap.apply(res)  # re-run
        self.assertEqual(len(j2.skipped), 5)
        self.assertEqual(ap.verify(res), [])
        clean = self.tmp / "clean"
        clean.mkdir()
        res2 = resolve(Choices(name="Rec", folder="Rec", picks=res.choices.picks, versions={}), CATALOG, clean)
        ap.apply(res2)
        self.assertEqual(snapshot(res.root), snapshot(res2.root))

    def test_rollback_removes_only_unchanged_items_it_created(self):
        res = self.plan()
        with self.assertRaises(ap.ApplyError) as cm:
            ap.apply(res, _write=self.failing_after(4))
        j = cm.exception.journal
        edited = res.root / j.files[0][0]
        edited.write_text("user edit", encoding="utf-8")
        removed, kept = ap.rollback(res, j)
        self.assertEqual(kept, [j.files[0][0]])
        self.assertEqual(edited.read_text(encoding="utf-8"), "user edit")
        self.assertTrue(res.root.exists(), "root kept because a modified file remains")
        self.assertEqual([p.name for p in res.root.rglob("*") if p.is_file()], [edited.name])

    def test_rollback_of_untouched_run_removes_everything_it_made(self):
        res = self.plan()
        with self.assertRaises(ap.ApplyError) as cm:
            ap.apply(res, _write=self.failing_after(3))
        ap.rollback(res, cm.exception.journal)
        self.assertFalse(res.root.exists())

    def test_foreign_files_block_creation_and_are_never_touched(self):
        res = self.plan()
        res.root.mkdir()
        (res.root / "notes.txt").write_text("mine", encoding="utf-8")
        with self.assertRaises(ap.ApplyError):
            ap.apply(res)
        self.assertEqual(sorted(p.name for p in res.root.iterdir()), ["notes.txt"])

    def test_modified_planned_file_is_a_conflict_not_overwritten(self):
        res = self.plan()
        ap.apply(res)
        (res.root / "README.md").write_text("changed", encoding="utf-8")
        (res.root / ".project.json").unlink()
        self.assertEqual(ap.classify_target(res)[0], "conflict")
        with self.assertRaises(ap.ApplyError):
            ap.apply(res)
        self.assertEqual((res.root / "README.md").read_text(encoding="utf-8"), "changed")

    def test_verify_detects_damage(self):
        res = self.plan()
        ap.apply(res)
        (res.root / "AGENTS.md").unlink()
        self.assertTrue(ap.verify(res))


class SafetyCheck(Tmp):
    def project(self, *extra):
        root = self.tmp / "S"
        r = cli_run(["S", "--out", str(self.tmp), "--yes", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "codex", "--distribution", "none", "--features",
                     "local_assets,user_testing", "--git", *extra])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return root

    def run_check(self, root):
        return subprocess.run([sys.executable, str(root / ".agent" / "safety_check.py")],
                              capture_output=True, text=True)

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_clean_project_passes(self):
        r = self.run_check(self.project())
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("OK", r.stdout)

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_planted_problems_are_found_without_printing_values(self):
        root = self.project()
        secret = "synthetic-" + "a" * 24
        (root / "src" / "app.py").write_text(f'api_key = "{secret}"\n', encoding="utf-8")
        (root / "src" / "key.txt").write_text(("-----BEGIN " + "PRIVATE KEY-----\nabc\n"), encoding="utf-8")
        (root / "src" / "ok.py").write_text('token = "your-token-here"\n', encoding="utf-8")  # placeholder: fine
        (root / "credentials.json").write_text("{}", encoding="utf-8")
        (root / "big.bin").write_bytes(b"0" * (6 * 1024 * 1024))
        (root / "cut.mov").write_bytes(b"x")
        (root / ".env").write_text("A=1", encoding="utf-8")
        git(root, "add", "-f", ".env")
        (root / "local" / "user-testing" / "participant-data" / "p.txt").write_text("x", encoding="utf-8")
        git(root, "add", "-f", "local/user-testing/participant-data/p.txt")
        r = self.run_check(root)
        out = r.stdout
        self.assertEqual(r.returncode, 1)
        for expect in ("FAIL  hardcoded_credential  src/app.py:1", "FAIL  private_key_block  src/key.txt:1",
                       "FAIL  secret_file_tracked  .env", "FAIL  local_only_tracked  local/user-testing/participant-data/p.txt",
                       "WARN  watched_file_name  credentials.json", "WARN  large_file_over_5MB  big.bin",
                       "WARN  watched_file_name  cut.mov"):
            self.assertIn(expect, out)
        self.assertNotIn("src/ok.py", out)
        self.assertNotIn(secret, out + r.stderr)
        self.assertNotIn("ABCDEF1234", out)

    def test_safety_module_is_the_shipped_script(self):
        shipped = (ROOT / "templates" / "v2" / "agent-safety-check.py").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as t:
            res = resolve(Choices(name="Z", folder="Z", picks=dict(category=["generic"], platform=["windows"],
                          ai=["codex"], state=["new"], distribution=["none"]), versions={}), CATALOG, t)
            self.assertEqual(res.files[".agent/safety_check.py"], shipped)

    def test_scripts_never_modify_files(self):
        src = (ROOT / "templates" / "v2" / "agent-safety-check.py").read_text(encoding="utf-8")
        for banned in (".unlink(", "rmtree", ".write_text(", "os.remove", "shutil", ".rename(", "urllib", "socket"):
            self.assertNotIn(banned, src)
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "open":
                self.assertTrue(node.args and isinstance(node.args[0], ast.Constant))
                self.assertEqual(node.args[0].value, "r", "scanner opens files read-only")


class SecretTemplates(Tmp):
    def test_env_example_has_placeholders_only_and_memory_forbids_secrets(self):
        root = self.make_project()
        env = (root / ".env.example").read_text(encoding="utf-8")
        self.assertTrue(all(l.startswith("#") or not l.strip() for l in env.splitlines()))
        mem = (root / ".agent" / "MEMORY.md").read_text(encoding="utf-8")
        self.assertIn("Never:", mem)
        self.assertIn("secret", mem)
        self.assertIn("configuration.md", " ".join(p.name for p in (root / "docs" / "developer").iterdir()))

    def make_project(self):
        r = cli_run(["Sec", "--out", str(self.tmp), "--yes", "--category", "generic", "--platform", "windows",
                     "--stack", "none", "--ai", "codex", "--distribution", "none", "--features", "sensitive_config",
                     "--no-git"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.tmp / "Sec"


if __name__ == "__main__":
    unittest.main()
