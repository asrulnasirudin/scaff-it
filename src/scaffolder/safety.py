"""Loads the Repository Safety Check, which is a single standalone script shipped into projects
as .agent/safety_check.py. One source of truth: templates/v2/agent-safety-check.py.
It is executed from source so no bytecode cache is written into the templates folder."""
import types

from .layers import TEMPLATES_DIR

_PATH = TEMPLATES_DIR / "v2" / "agent-safety-check.py"
_mod = types.ModuleType("project_safety_check")
_mod.__file__ = str(_PATH)
exec(compile(_PATH.read_text(encoding="utf-8"), str(_PATH), "exec"), _mod.__dict__)

scan = _mod.scan
