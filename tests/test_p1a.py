"""P1a tests: layers, roles, descriptor, path safety, architecture rules (New state)."""
import ast
from datetime import date
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(ROOT))

from scaffolder import pathsafe  # noqa: E402
from scaffolder.layers import Layer, LayerError, _load_one, load_catalog  # noqa: E402
from scaffolder.resolve import Choices, ResolveError, resolve  # noqa: E402

NEW = ROOT / "new_project.py"
CATALOG = load_catalog()
BASE_ARGS = ["--platform", "windows", "--stack", "none", "--ai", "none", "--distribution", "none", "--yes"]


def cli(args, stdin=""):
    return subprocess.run([sys.executable, str(NEW), *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8")


def tree(root):
    return {p.relative_to(root).as_posix(): (None if p.is_dir() else p.read_bytes())
            for p in sorted(root.rglob("*"))}


def choices(name="Demo", folder="Demo", **picks):
    picks.setdefault("state", ["new"])
    picks.setdefault("distribution", ["none"])
    picks.setdefault("platform", ["windows"])
    return Choices(name=name, folder=folder, picks=picks, versions={})


class Tmp(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.tmp = Path(self._t.name).resolve()


class JsonContributions(Tmp):
    def plan(self, *parts, node=False):
        catalog = dict(CATALOG)
        features = []
        for index, part in enumerate(parts):
            ident = f"merge_{index}"
            layer = Layer("feature", ident, ident, "1", {"json_merge": part})
            catalog[layer.ref] = layer
            features.append(ident)
        selected = choices(category=["tool"], feature=features,
                           stack=["node_typescript"] if node else [])
        selected.git = False
        return resolve(selected, catalog, self.tmp)

    def test_combines_template_and_multiple_features_with_verified_hash(self):
        result = self.plan(
            {"package.json": {"scripts": {"format": "prettier . --check"},
                              "devDependencies": {"example-formatter": "1.0.0"}}},
            {"package.json": {"scripts": {"storybook": "storybook dev"}}}, node=True)
        package = json.loads(result.files["package.json"])
        self.assertEqual(package["name"], "demo")
        self.assertEqual(package["scripts"], {"lint": "eslint .", "format": "prettier . --check",
                                               "storybook": "storybook dev"})
        self.assertIn("eslint", package["devDependencies"])
        self.assertEqual(package["devDependencies"]["example-formatter"], "1.0.0")
        record = next(x for x in result.descriptor["scaffold"]["managed_files"]
                      if x["path"] == "package.json")
        self.assertEqual(record["sha256"], hashlib.sha256(result.files["package.json"].encode()).hexdigest())
        self.assertFalse(result.root.exists())

    def test_creates_new_object_and_reuses_identical_values(self):
        part = {"config.json": {"name": "@@SLUG@@", "nested": {"enabled": True}, "items": ["a"]}}
        result = self.plan(part, part)
        self.assertEqual(json.loads(result.files["config.json"]),
                         {"name": "demo", "nested": {"enabled": True}, "items": ["a"]})
        self.assertEqual(result.files, self.plan(part, part).files)

    def test_rejects_conflicts_with_field_and_both_layers(self):
        with self.assertRaisesRegex(ResolveError, r"config.json.*scripts.build.*feature:merge_0.*feature:merge_1"):
            self.plan({"config.json": {"scripts": {"build": "one"}}},
                      {"config.json": {"scripts": {"build": "two"}}})
        with self.assertRaisesRegex(ResolveError, r"package.json.*scripts.lint.*template.*feature:merge_0"):
            self.plan({"package.json": {"scripts": {"lint": "replacement"}}}, node=True)

    def test_rejects_type_and_array_conflicts(self):
        for left, right in [(True, 1), ({"a": 1}, "text"), (["a"], ["b"]), ([True], [1])]:
            with self.subTest(left=left, right=right), self.assertRaises(ResolveError):
                self.plan({"config.json": {"value": left}}, {"config.json": {"value": right}})

    def test_rejects_unsafe_reserved_and_directory_paths(self):
        for path in ["../escape.json", ".project.json", ".gitignore", "src", "CON.json"]:
            with self.subTest(path=path), self.assertRaises(ResolveError):
                self.plan({path: {"value": 1}})

    def test_rejects_non_object_or_invalid_base_and_non_json_values(self):
        with self.assertRaisesRegex(ResolveError, "cannot merge JSON"):
            self.plan({"README.md": {"value": 1}})
        for invalid in [float("nan"), date(2026, 11, 1)]:
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ResolveError, "cannot merge JSON"):
                self.plan({"config.json": {"value": invalid}})

    def test_layer_loader_rejects_non_object_contributions(self):
        layer = self.tmp / "sample.toml"
        header = 'id="sample"\nkind="feature"\nlabel="Sample"\nversion="1"\nprofile_format=1\n'
        for content in ['json_merge = "bad"', '[json_merge]\n"package.json" = "bad"']:
            layer.write_text(header + content, encoding="utf-8")
            with self.subTest(content=content), self.assertRaisesRegex(LayerError, "json_merge"):
                _load_one(layer, "feature")
        layer.write_text(header + '[json_merge."package.json".scripts]\nformat="example --check"',
                         encoding="utf-8")
        loaded = _load_one(layer, "feature")
        self.assertEqual(loaded.data["json_merge"]["package.json"]["scripts"],
                         {"format": "example --check"})

    def test_written_files_match_plan_and_existing_project_is_preserved(self):
        from scaffolder.apply import ApplyError, apply, verify
        result = self.plan({"settings/config.json": {"enabled": True}})
        apply(result)
        self.assertEqual(verify(result), [])
        path = result.root / "settings/config.json"
        path.write_text('{"enabled": false}', encoding="utf-8")
        with self.assertRaises(ApplyError):
            apply(result)
        self.assertEqual(json.loads(path.read_text())["enabled"], False)

    def test_remove_clears_earlier_contributions(self):
        from scaffolder.resolve import merge
        layers = [
            Layer("feature", "first", "First", "1", {"json_merge": {"config.json": {"old": True}}}),
            Layer("feature", "remove", "Remove", "1", {"remove": ["config.json"]}),
            Layer("feature", "last", "Last", "1", {"json_merge": {"config.json": {"new": True}}}),
        ]
        config = merge(layers[:2], choices())
        self.assertNotIn("config.json", config["json_merge"])
        config = merge(layers, choices())
        self.assertEqual(config["json_merge"]["config.json"], [("feature:last", {"new": True})])


class ExampleProjects(Tmp):
    def make_sample_app(self, ai="codex"):
        r = cli(["SampleApp", "--category", "app", "--platform", "windows", "--stack", "electron",
                 "--ai", ai, "--distribution", "installer", "--out", str(self.tmp), "--yes"])
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return self.tmp / "SampleApp"

    def test_sample_app_structure(self):
        root = self.make_sample_app()
        for need in ("AGENTS.md", "PROJECT_SPEC.md", "README.md", ".project.json", ".gitignore",
                     "docs/user/README.md", "docs/developer/README.md", "src/.gitkeep", "tests/.gitkeep",
                     "assets/.gitkeep", ".agent/MEMORY.md", ".agent/CODEX.md", ".agent/CHECKPOINT.md",
                     ".agent/PLANS.md", ".agent/DECISIONS.md", ".agent/QA_CHECKLIST.md", ".agent/check.py",
                     ".agent/context/README.md", ".agent/phases/README.md", ".agent/reviews/README.md"):
            self.assertTrue((root / need).is_file(), need)
        # tool-created roles are never scaffolded; no READMEs in src/tests/build/dist
        for gone in ("build", "dist", "src/README.md", "tests/README.md", "CLAUDE.md", "GEMINI.md"):
            self.assertFalse((root / gone).exists(), gone)
        ign = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
        for line in ("/build/", "/dist/", ".env", "!.env.example", "node_modules/"):
            self.assertIn(line, ign)
        self.assertNotIn("credentials.*", ign)  # watch patterns are not ignored (P-4)

    def test_descriptor_fields_and_hashes(self):
        root = self.make_sample_app()
        d = json.loads((root / ".project.json").read_text(encoding="utf-8"))
        self.assertEqual((d["schema_version"], d["category"], d["state"], d["stack"], d["stack_status"]),
                         (1, "app", "new", ["electron"], "chosen"))
        self.assertEqual(d["platforms"], [{"id": "windows"}])
        self.assertEqual(d["targets"], [])
        self.assertEqual(d["layout"]["roles"]["dist"], {"path": "dist", "origin": "tool_created"})
        self.assertEqual(d["git"]["commit_policy"], "ask")
        self.assertEqual(d["development"]["ai"], ["codex"])
        self.assertEqual(d["distribution"]["type"], "installer")
        self.assertEqual(d["security"]["large_file_warn_mb"], 5)
        self.assertIn("credentials.*", d["security"]["watch_patterns"])
        self.assertEqual(d["answer_source"]["category"], "user")
        self.assertIn({"kind": "ai", "id": "agent_workspace", "version": "1", "implied": True},
                      d["profiles"]["layers"])
        for m in d["scaffold"]["managed_files"]:
            self.assertEqual(hashlib.sha256((root / m["path"]).read_bytes()).hexdigest(), m["sha256"], m["path"])
        self.assertNotIn(".project.json", [m["path"] for m in d["scaffold"]["managed_files"]])
        text = (root / ".project.json").read_text(encoding="utf-8")
        self.assertNotIn(str(self.tmp), text)  # no machine-specific paths

    def test_check_script_fails_then_passes_when_filled(self):
        root = self.make_sample_app()
        r = subprocess.run([sys.executable, str(root / ".agent" / "check.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        for rel in ("PROJECT_SPEC.md", "docs/developer/architecture.md"):
            p = root / rel
            p.write_text(p.read_text(encoding="utf-8").replace("TODO", "done").replace("TO CONFIRM", "done"),
                         encoding="utf-8")
        r = subprocess.run([sys.executable, str(root / ".agent" / "check.py")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_sample_blender_addon_style(self):
        r = cli(["Sample Blender Addon", "--category", "extension", "--platform", "windows", "--target", "blender@5.2",
                 "--stack", "python", "--ai", "codex", "--distribution", "extension_zip",
                 "--out", str(self.tmp), "--yes"])
        self.assertEqual(r.returncode, 0, r.stderr)
        root = self.tmp / "Sample-Blender-Addon"
        d = json.loads((root / ".project.json").read_text(encoding="utf-8"))
        self.assertEqual(d["slug"], "sample-blender-addon")
        self.assertEqual(d["targets"], [{"id": "blender", "version": "5.2"}])
        self.assertEqual(d["toolchain"], {"python": ">=3.11", "blender": "5.2"})
        self.assertEqual(d["distribution"]["type"], "extension_zip")
        self.assertTrue((root / ".agent" / "CODEX.md").is_file())

    def test_unspecified_target_version_is_not_guessed(self):
        r = cli(["X", "--category", "extension", "--platform", "windows", "--target", "blender", "--stack", "python",
                 "--ai", "none", "--distribution", "none", "--out", str(self.tmp), "--yes"], stdin="\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads((self.tmp / "X" / ".project.json").read_text(encoding="utf-8"))
        self.assertNotIn("blender", d["toolchain"])
        self.assertEqual(d["targets"], [{"id": "blender"}])

    def test_ai_selection_controls_pointer_files(self):
        root = self.make_sample_app(ai="claude_code,antigravity")
        self.assertEqual((root / "CLAUDE.md").read_text(encoding="utf-8").strip(), "@AGENTS.md")
        self.assertIn("AGENTS.md", (root / "GEMINI.md").read_text(encoding="utf-8"))
        self.assertFalse((root / ".agent" / "CODEX.md").exists())
        self.assertTrue((root / ".agent" / "MEMORY.md").exists())

    def test_no_ai_means_no_agent_folder(self):
        r = cli(["Plain", "--category", "website", "--platform", "web", "--stack", "static_html", "--ai", "none",
                 "--distribution", "none", "--out", str(self.tmp), "--yes"])
        self.assertEqual(r.returncode, 0, r.stderr)
        root = self.tmp / "Plain"
        self.assertFalse((root / ".agent").exists())
        self.assertTrue((root / "AGENTS.md").exists())
        self.assertNotIn(".agent/MEMORY.md", (root / "AGENTS.md").read_text(encoding="utf-8"))

    def test_interactive_session(self):
        # name, location, description, category, platform, stack, ai, distribution,
        # 3 extras (n), git (y), workflow (Enter), first commit (n), then Create
        stdin = (f"SampleApp\n{self.tmp}\nA media library\napp\nwindows\nelectron\ncodex\ninstaller\n"
                 "n\nn\nn\ny\n\nn\nc\n")
        r = cli([], stdin)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        self.assertTrue((self.tmp / "SampleApp" / ".project.json").exists())
        d = json.loads((self.tmp / "SampleApp" / ".project.json").read_text(encoding="utf-8"))
        self.assertEqual(d["answer_source"]["state"], "default")
        self.assertEqual(d["answer_source"]["stack"], "user")

    def test_declining_creates_nothing(self):
        r = cli(["Nope", "--category", "app", *BASE_ARGS[:-1], "--out", str(self.tmp)], stdin="n\n")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(list(self.tmp.iterdir()), [])
        r = cli(["Nope", "--category", "app", *BASE_ARGS[:-1], "--out", str(self.tmp)], stdin="")
        self.assertEqual(list(self.tmp.iterdir()), [])

    def test_refuses_non_empty_folder_and_leaves_it(self):
        (self.tmp / "Keep").mkdir()
        (self.tmp / "Keep" / "a.txt").write_text("precious", encoding="utf-8")
        r = cli(["Keep", "--category", "app", *BASE_ARGS, "--out", str(self.tmp)])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(sorted(tree(self.tmp / "Keep")), ["a.txt"])

    def test_generation_is_deterministic(self):
        a, b = self.tmp / "a", self.tmp / "b"
        a.mkdir(), b.mkdir()
        for out in (a, b):
            r = cli(["Same", "--category", "game", "--platform", "windows", "--target", "none", "--stack", "godot", "--ai", "codex",
                     "--distribution", "none", "--out", str(out), "--yes"])
            self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(tree(a / "Same"), tree(b / "Same"))


class Matrix(unittest.TestCase):
    CASES = [
        dict(category=["app"], stack=["electron"], ai=["codex"], distribution=["installer"]),
        dict(category=["website"], platform=["web"], stack=["static_html"], distribution=["web_deploy"]),
        dict(category=["game"], stack=["godot"], ai=["claude_code", "antigravity"]),
        dict(category=["teaching"], ai=["codex"]),
        dict(category=["creative"], ai=["codex", "claude_code"]),
        dict(category=["extension"], target=["blender"], stack=["python"], distribution=["extension_zip"]),
        dict(category=["extension"], target=["after_effects"]),
        dict(category=["game"], target=["unreal_engine"]),
        dict(category=["app"], platform=["windows", "macos", "linux"], stack=["node_typescript"]),
    ]

    def test_every_case_resolves_with_clean_paths(self):
        with tempfile.TemporaryDirectory() as t:
            for i, case in enumerate(self.CASES):
                with self.subTest(case=case):
                    res = resolve(choices(f"P{i}", f"P{i}", **case), CATALOG, t)
                    self.assertIn(".project.json", res.files)
                    self.assertIn("AGENTS.md", res.files)
                    self.assertFalse([p for p in res.files if p.startswith(("build/", "dist/"))])
                    self.assertFalse([p for p in res.files if p in ("src/README.md", "tests/README.md")])
                    json.loads(res.files[".project.json"])

    def test_no_unfilled_tokens_in_generated_text(self):
        with tempfile.TemporaryDirectory() as t:
            for case in self.CASES:
                res = resolve(choices("P", "P", **case), CATALOG, t)
                for path, text in res.files.items():
                    self.assertIsNone(re.search(r"@@[A-Z_]+@@", text), f"{path} has an unfilled token")


class RequiresConflicts(unittest.TestCase):
    def problems(self, **picks):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(ResolveError) as cm:
                resolve(choices(**picks), CATALOG, t)
            return " | ".join(cm.exception.problems)

    def test_conflict_target_with_app(self):
        self.assertIn("cannot be combined", self.problems(category=["app"], target=["blender"]))

    def test_extension_needs_target(self):
        self.assertIn("requires", self.problems(category=["extension"]))

    def test_stack_requires_category(self):
        self.assertIn("requires", self.problems(category=["website"], stack=["electron"]))

    def test_distribution_requires_platform(self):
        self.assertIn("requires", self.problems(category=["website"], platform=["web"], distribution=["installer"]))

    def test_unknown_layer_lists_choices(self):
        self.assertIn("Available:", self.problems(category=["nonsense"]))

    def test_single_choice_kinds(self):
        self.assertIn("exactly one category", self.problems(category=["app", "game"]))
        self.assertIn("exactly one category", self.problems())


def write_layer(dirpath, kind, ident, body):
    d = Path(dirpath) / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{ident}.toml").write_text(
        f'id = "{ident}"\nkind = "{kind}"\nlabel = "{ident}"\nversion = "1"\nprofile_format = 1\n{body}', encoding="utf-8")


class PathSafety(Tmp):
    def catalog_with(self, body, kind="stack", ident="evil"):
        layers = self.tmp / "layers"
        for k in ("base", "state", "platform", "category", "distribution"):
            for f in (ROOT / "layers" / k).glob("*.toml"):
                (layers / k).mkdir(parents=True, exist_ok=True)
                (layers / k / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
        write_layer(layers, kind, ident, body)
        return load_catalog(layers)

    def attempt(self, body):
        cat = self.catalog_with(body)
        with self.assertRaises(ResolveError) as cm:
            resolve(choices(category=["app"], stack=["evil"]), cat, self.tmp / "out")
        return " | ".join(cm.exception.problems)

    def test_parent_traversal(self):
        self.assertIn("leave the project", self.attempt('[files]\n"../outside.txt" = "v2/readme.md"\n'))
        self.assertIn("leave the project", self.attempt('[files]\n"a/../../b.txt" = "v2/readme.md"\n'))
        self.assertIn("leave the project", self.attempt('[dirs]\n"x/../../y" = "p"\n'))

    def test_absolute_paths(self):
        self.assertIn("absolute", self.attempt('[files]\n"/etc/passwd" = "v2/readme.md"\n'))
        self.assertIn("absolute", self.attempt('[files]\n"C:/x.txt" = "v2/readme.md"\n'))
        self.assertIn("absolute", self.attempt('[files]\n"~/x.txt" = "v2/readme.md"\n'))

    def test_role_path_escape(self):
        self.assertIn("leave the project", self.attempt('[roles]\nsource = { path = "../src", origin = "scaffolded" }\n'))

    def test_backslash_reserved_and_invalid_names(self):
        self.assertIn("backslashes", self.attempt('[files]\n"a\\\\b.txt" = "v2/readme.md"\n'))
        self.assertIn("reserved", self.attempt('[files]\n"nul.txt" = "v2/readme.md"\n'))
        self.assertIn("invalid", self.attempt('[files]\n"a?b.txt" = "v2/readme.md"\n'))
        self.assertIn("ends with", self.attempt('[files]\n"name. " = "v2/readme.md"\n'))

    def test_case_collision(self):
        self.assertIn("letter case", self.attempt('[files]\n"Doc.md" = "v2/readme.md"\n"doc.md" = "v2/readme.md"\n'))

    def test_role_conflict_and_file_dir_clash(self):
        self.assertIn("same folder", self.attempt('[roles]\ntests = { path = "src", origin = "scaffolded" }\n'))
        self.assertIn("both a file and a folder", self.attempt('[files]\n"src" = "v2/readme.md"\n'))

    def test_missing_template(self):
        self.assertIn("Missing template", self.attempt('[files]\n"a.md" = "v2/nope.md"\n'))

    def test_too_long_path(self):
        long = "/".join(["d" * 90] * 3)
        self.assertIn("too long", self.attempt(f'[files]\n"{long}/f.md" = "v2/readme.md"\n'))

    def test_newer_format_and_unknown_keys_rejected(self):
        layers = self.tmp / "l2"
        d = layers / "base"
        d.mkdir(parents=True)
        (d / "base.toml").write_text('id="base"\nkind="base"\nlabel="b"\nversion="1"\nprofile_format=99\n', encoding="utf-8")
        with self.assertRaisesRegex(LayerError, "newer scaffolder"):
            load_catalog(layers)
        (d / "base.toml").write_text('id="base"\nkind="base"\nlabel="b"\nversion="1"\nprofile_format=1\nbogus=1\n', encoding="utf-8")
        with self.assertRaisesRegex(LayerError, "unknown key"):
            load_catalog(layers)

    def test_folder_names(self):
        for bad in ("../evil", "a/b", "..", "CON", "bad:name", "x\\y", "trail.", ""):
            with self.subTest(folder=bad):
                with self.assertRaises(ResolveError):
                    resolve(choices(folder=bad, category=["teaching"]), CATALOG, self.tmp)

    def test_system_folder_symlink_and_nesting(self):
        errs, _ = pathsafe.check_target_root(Path("/etc/proj"))
        self.assertTrue(errs)
        errs, _ = pathsafe.check_target_root(Path("/proj"))
        self.assertTrue(errs)
        (self.tmp / "outer").mkdir()
        (self.tmp / "outer" / ".project.json").write_text("{}", encoding="utf-8")
        res = resolve(choices(folder="inner", category=["teaching"]), CATALOG, self.tmp / "outer")
        self.assertTrue([w for w in res.warnings if "nest" in w])

    def test_symlink_root_is_rejected(self):
        real = self.tmp / "real"
        real.mkdir()
        try:
            (self.tmp / "link").symlink_to(real, target_is_directory=True)
        except OSError as error:
            if getattr(error, "winerror", None) != 1314:
                raise
            self.skipTest("Windows symlink privilege unavailable")
        with self.assertRaises(ResolveError):
            resolve(choices(folder="link", category=["teaching"]), CATALOG, self.tmp)

    def test_reparse_point_attribute_is_recognized(self):
        with patch.object(Path, "lstat", return_value=SimpleNamespace(st_mode=0, st_file_attributes=0x400)):
            self.assertTrue(pathsafe.is_link(self.tmp / "junction"))

    def test_linked_parent_is_rejected(self):
        parent = self.tmp / "linked-parent"
        with patch.object(pathsafe, "is_link", side_effect=lambda path: path == parent):
            errors, _ = pathsafe.check_target_root(parent / "project")
        self.assertTrue(any("reparse" in error for error in errors))

    def test_nested_junction_blocks_apply_without_external_writes(self):
        from scaffolder import apply as application
        root = self.tmp / "project"
        root.mkdir()
        junction = root / "src"
        junction.mkdir()
        res = SimpleNamespace(root=root, dirs=["src"], files={"src/demo.py": "example"})
        with patch.object(application, "is_link", side_effect=lambda path: path == junction):
            state, _ = application.classify_target(res)
            self.assertEqual(state, "conflict")
            with self.assertRaises(application.ApplyError):
                application.apply(res)
        self.assertEqual(list(junction.iterdir()), [])

    def test_cli_rejects_escape_and_writes_nothing(self):
        out = self.tmp / "out"
        out.mkdir()
        r = cli(["x", "--folder", "../evil", "--category", "app", *BASE_ARGS, "--out", str(out)])
        self.assertEqual(r.returncode, 2)
        self.assertEqual(list(self.tmp.iterdir()), [out])
        self.assertEqual(list(out.iterdir()), [])


class ArchitectureRules(unittest.TestCase):
    CORE = sorted((ROOT / "scaffolder").glob("*.py")) + [NEW]
    TECH = re.compile(r"\b(electron|blender|react|angular|vue|godot|unity|unreal|premiere|after_effects|npm|"
                      r"django|flask|flutter|bpy|gdscript|typescript)\b", re.I)
    NET = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib", "xmlrpc", "requests",
           "httpx", "aiohttp", "websockets", "asyncio", "imaplib", "poplib", "webbrowser"}

    def test_core_has_no_technology_names(self):
        for f in self.CORE:
            hits = self.TECH.findall(f.read_text(encoding="utf-8"))
            self.assertEqual(hits, [], f"{f.name} mentions technology names: {hits}")

    def test_core_imports_no_network_modules(self):
        for f in self.CORE:
            tree_ = ast.parse(f.read_text(encoding="utf-8"))
            for node in ast.walk(tree_):
                mods = []
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    mods = [node.module]
                for m in mods:
                    self.assertNotIn(m.split(".")[0], self.NET, f"{f.name} imports {m}")

    def test_generated_check_script_is_network_free(self):
        text = (ROOT / "templates" / "v2" / "agent-check.py.tpl").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(text.replace("@@MUSTFILL@@", "[]"))):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module]
                for n in names:
                    self.assertNotIn(n.split(".")[0], self.NET)

    def test_layer_data_is_consistent(self):
        refs = set(CATALOG)
        used = set()
        for l in CATALOG.values():
            used.update(l.data.get("files", {}).values())
            for key in ("requires", "conflicts", "implies", "recommends"):
                for entry in l.data.get(key, []):
                    for alt in entry.split("|"):
                        kind, _, ident = alt.partition(":")
                        if ident == "*":
                            self.assertTrue([r for r in refs if r.startswith(kind + ":")], f"{l.ref} {key} {alt}")
                        else:
                            self.assertIn(f"{kind}:{ident}", refs, f"{l.ref} {key} {alt}")
        on_disk = {p.relative_to(ROOT / "templates").as_posix() for p in (ROOT / "templates" / "v2").rglob("*")
                   if p.is_file() and not p.name.startswith("git-workflow-")}  # workflows are discovered by name
        self.assertEqual(sorted(used - on_disk), [], "layers reference missing templates")
        self.assertEqual(sorted(on_disk - used), [], "templates never used by any layer")


if __name__ == "__main__":
    unittest.main()


class LintScaffolds(Tmp):
    def test_stack_specific_lint_files_are_rendered_and_tracked(self):
        import tomllib
        for stack in ("python", "node_typescript", None):
            with self.subTest(stack=stack):
                c = choices(category=["tool"], stack=[stack] if stack else [])
                c.git = False
                res = resolve(c, CATALOG, self.tmp)
                tracked = {item["path"] for item in res.descriptor["scaffold"]["managed_files"]}
                if stack == "python":
                    cfg = tomllib.loads(res.files["ruff.toml"])
                    self.assertIn("F", cfg["lint"]["select"])
                    self.assertIn("ruff.toml", tracked)
                    self.assertIn("python -m ruff check .", res.files["AGENTS.md"])
                    self.assertNotIn("package.json", res.files)
                elif stack == "node_typescript":
                    pkg = json.loads(res.files["package.json"])
                    self.assertEqual(pkg["name"], "demo")
                    self.assertEqual(pkg["scripts"]["lint"], "eslint .")
                    self.assertIn("eslint.config.mjs", tracked)
                    self.assertNotIn("ruff.toml", res.files)
                else:
                    self.assertNotIn("ruff.toml", res.files)
                    self.assertNotIn("package.json", res.files)
