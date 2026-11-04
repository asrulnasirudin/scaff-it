"""Preview and apply optional lint setup; never install without explicit consent."""
import json
import os
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from ..layers import TEMPLATES_DIR
from ..pathsafe import is_link, linked_ancestor
from ..render import fill
from ..resolve import slugify

SUPPORTED_STACKS = ("python", "node_typescript")


def bundled_ruff() -> Path | None:
    """Locate the native checker shipped with the portable app, not its bootloader."""
    if not getattr(sys, "frozen", False):
        return None
    return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "tools" / "ruff.exe"


def supports(stacks: list) -> bool:
    return len(stacks) == 1 and stacks[0] in SUPPORTED_STACKS


class LintError(Exception):
    """Lint setup cannot safely continue."""


@dataclass
class LintPlan:
    root: Path
    stack: str
    changes: dict = field(default_factory=dict)
    before: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


def _read(root: Path, name: str) -> str | None:
    path = root / name
    if linked_ancestor(path):
        raise LintError(f"Refusing linked path: {path}")
    return path.read_text(encoding="utf-8") if path.exists() else None


def _template(name: str) -> str:
    return (TEMPLATES_DIR / "v2" / name).read_text(encoding="utf-8")


def plan(root: Path, stack: str | None = None) -> LintPlan:
    """Inspect one project, preserving existing linter configuration and scripts."""
    root = Path(root).expanduser().absolute()
    if linked_ancestor(root) or not root.is_dir():
        raise LintError("Choose an existing real project directory, not a link.")
    package_text = _read(root, "package.json")
    py_text = _read(root, "pyproject.toml")
    pyproject = tomllib.loads(py_text) if py_text else {}
    if stack is None:
        python = py_text is not None or (root / "requirements.txt").exists() or (root / "ruff.toml").exists()
        if bool(package_text) == bool(python):
            raise LintError("Cannot choose one language automatically. Pass --stack python or --stack node_typescript.")
        stack = "node_typescript" if package_text else "python"
    if stack not in SUPPORTED_STACKS:
        raise LintError("Automatic lint setup currently supports python and node_typescript only.")
    result = LintPlan(root, stack)
    if stack == "node_typescript":
        # Watch even unchanged manifests: contributions may already contain all lint fields.
        result.before["package.json"] = package_text
        for name in ("package-lock.json", "npm-shrinkwrap.json"):
            result.before[name] = _read(root, name)

    def propose(name, content):
        old = _read(root, name)
        result.before[name] = old
        if old != content:
            result.changes[name] = content

    if stack == "python":
        tools = pyproject.get("tool", {})
        ruff = any(_read(root, n) is not None for n in ("ruff.toml", ".ruff.toml")) or "ruff" in tools
        other = any((root / n).exists() for n in (".flake8", ".pylintrc", "pylintrc")) or any(n in tools for n in ("pylint", "flake8"))
        setup = _read(root, "setup.cfg") or ""
        other = other or "[flake8]" in setup or "[pylint" in setup
        if other and not ruff:
            raise LintError("An existing Python linter was found. Keep its setup; automatic conversion is not supported.")
        if ruff:
            result.notes.append("Reuse existing Ruff configuration.")
        else:
            propose("ruff.toml", _template("lint-ruff.toml"))
        result.notes.append("Run the included Ruff checker without fixes; no Python installation or download needed."
                            if bundled_ruff() else
                            "Install Ruff 0.17.3 in a dedicated .venv-lint environment; run its check without fixes.")
        ignores = [".venv-lint/", ".ruff_cache/"]
    else:
        for name in ("yarn.lock", "pnpm-lock.yaml", "bun.lock", "bun.lockb"):
            if (root / name).exists():
                raise LintError("This project uses another package manager. Automatic installation currently supports npm only.")
        package = json.loads(package_text) if package_text else {"name": slugify(root.name) or "project", "private": True}
        if not isinstance(package, dict) or any(not isinstance(package.get(k, {}), dict) for k in ("scripts", "dependencies", "devDependencies")):
            raise LintError("package.json must contain an object with valid dependency and script objects.")
        manager = package.get("packageManager", "npm")
        if not isinstance(manager, str) or not (manager == "npm" or manager.startswith("npm@")) or package.get("workspaces"):
            raise LintError("Use a standalone npm project; workspace/package-manager migration is not supported.")
        if any(root.glob(".eslintrc*")) or "eslintConfig" in package:
            raise LintError("Legacy ESLint configuration found. Upgrade it separately before automatic setup.")
        configs = list(root.glob("eslint.config.*"))
        if any(is_link(p) for p in configs):
            raise LintError("Refusing linked ESLint configuration.")
        if not configs:
            if any(root.glob("biome.json*")) or "eslint" not in package.get("scripts", {}).get("lint", "eslint"):
                raise LintError("An existing lint tool was found. Automatic replacement is not supported.")
            propose("eslint.config.mjs", _template("lint-eslint.mjs"))
            defaults = json.loads(fill(_template("lint-node-package.json"), {"SLUG": "project"}))["devDependencies"]
        else:
            result.notes.append("Reuse existing ESLint configuration and declared plugin versions.")
            defaults = {"eslint": json.loads(fill(_template("lint-node-package.json"), {"SLUG": "project"}))["devDependencies"]["eslint"]}
        deps = package.setdefault("devDependencies", {})
        for name, version in defaults.items():
            if name not in package.get("dependencies", {}) and name not in deps:
                deps[name] = version
        package.setdefault("scripts", {}).setdefault("lint", "eslint .")
        if not package_text or package != json.loads(package_text):
            propose("package.json", json.dumps(package, indent=2, ensure_ascii=False) + "\n")
        result.notes.append("Run npm install --ignore-scripts --include=dev, preserving the combined package settings "
                            "and installing declared application and development dependencies; then check with local ESLint.")
        ignores = ["node_modules/"]
    old_ignore = _read(root, ".gitignore") or ""
    missing = [line for line in ignores if line not in old_ignore.splitlines()]
    if missing:
        propose(".gitignore", old_ignore.rstrip("\n") + "\n\n# Lint tools\n" + "\n".join(missing) + "\n")
    return result


def preview(plan: LintPlan, install: bool) -> None:
    print(f"\nLint setup: {plan.root} ({plan.stack})")
    for name in plan.changes:
        print(f"  {'Update' if plan.before[name] is not None else 'Create'} {name}")
    if not plan.changes:
        print("  Existing configuration will be kept.")
    if install:
        for note in plan.notes:
            print(f"  {note}")
        if plan.stack == "python" and bundled_ruff():
            print("  The bundled check runs locally without downloading packages. Existing code issues may be reported.")
        else:
            print("  Installation downloads packages. The initial lint check may report existing code issues.")
    else:
        print("  Configure only; no packages will be installed and no lint check will run.")


def apply(plan: LintPlan) -> None:
    """Verify the preview is still current before writing any planned changes."""
    for name, old in plan.before.items():
        if _read(plan.root, name) != old:
            raise LintError(f"{name} changed since preview. Run setup again.")
    for name, content in plan.changes.items():
        (plan.root / name).write_text(content, encoding="utf-8")


def install_and_check(plan: LintPlan) -> bool:
    """Run only after consent; failure leaves the project available for retry."""
    root = plan.root
    if linked_ancestor(root):
        raise LintError("Project directory became a link; refusing installation.")
    for name, old in plan.before.items():
        expected = plan.changes.get(name, old)
        if _read(root, name) != expected:
            raise LintError(f"{name} changed since setup preview. Run setup again before installing.")
    if plan.stack == "python" and bundled_ruff():
        tool = bundled_ruff()
        if not tool.is_file():
            raise LintError("The bundled checker is missing. Extract the complete Windows ZIP and try again.")
        commands = [[str(tool), "check", ".", "--extend-exclude", ".venv-lint"]]
    elif plan.stack == "python":
        env = root / ".venv-lint"
        exe = env / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if env.exists() and (linked_ancestor(env) or not exe.is_file()):
            raise LintError(".venv-lint is not a usable environment. Keep it and choose another location manually.")
        commands = [] if env.exists() else [[sys.executable, "-m", "venv", str(env)]]
        commands += [[str(exe), "-m", "pip", "install", "ruff==0.17.3"],
                     [str(exe), "-m", "ruff", "check", ".", "--extend-exclude", ".venv-lint"]]
    else:
        if linked_ancestor(root / "node_modules"):
            raise LintError("Refusing linked node_modules directory.")
        npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
        if not npm:
            raise LintError("npm is unavailable. Install Node.js, then retry lint setup.")
        eslint = root / "node_modules" / ".bin" / ("eslint.cmd" if os.name == "nt" else "eslint")
        commands = [[npm, "install", "--ignore-scripts", "--include=dev"], [str(eslint), "."]]
    for command in commands:
        print("Running: " + subprocess.list2cmdline(command), flush=True)
        try:
            completed = subprocess.run(command, cwd=root, check=False)
        except OSError as exc:
            raise LintError(f"Could not run the tool: {exc}. Configuration is kept; retry when ready.") from exc
        if completed.returncode:
            print("Lint setup/check did not pass. Files are kept; review the output and retry. No fixes were applied.")
            return False
    print("Lint setup and initial check passed.")
    return True


def consent(prompt: str) -> bool:
    try:
        return input(prompt + " [y/N]: ").strip().lower() in ("y", "yes")
    except EOFError:
        return False
