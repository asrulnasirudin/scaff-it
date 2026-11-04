"""Layer catalog: read, validate and describe layer files (data only, no technology knowledge)."""
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYERS_DIR = ROOT / "layers"
TEMPLATES_DIR = ROOT / "templates"

SUPPORTED_FORMAT = 1
KIND_ORDER = ("base", "category", "platform", "target", "stack", "state", "ai", "distribution", "feature")
ROLES = ("source", "tests", "build", "dist", "docs_user", "docs_dev", "assets", "ai", "legacy", "local", "research")
ORIGINS = ("scaffolded", "tool_created", "committed")

ALLOWED_KEYS = {
    "id", "kind", "label", "version", "profile_format", "description", "hidden", "ask_version", "default",
    "requires", "conflicts", "implies", "recommends",
    "roles", "dirs", "files", "remove", "ignore", "qa", "questions", "commands", "conventions",
    "donts", "warnings", "recommendations", "must_fill", "protected_paths",
    "security", "toolchain", "distribution", "json_merge",
}
SECURITY_KEYS = {"secret", "local_only", "generated", "watch", "large_file_warn_mb"}


class LayerError(Exception):
    """A layer file is missing, malformed or too new for this tool."""


@dataclass
class Layer:
    kind: str
    id: str
    label: str
    version: str
    data: dict = field(repr=False)

    @property
    def ref(self):
        return f"{self.kind}:{self.id}"

    @property
    def hidden(self):
        return bool(self.data.get("hidden"))


def _load_one(path, kind_dir):
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise LayerError(f"{path.name}: invalid TOML ({e})")
    where = f"{kind_dir}/{path.name}"
    for key in ("id", "kind", "label", "version", "profile_format"):
        if key not in data:
            raise LayerError(f"{where}: missing '{key}'")
    unknown = sorted(set(data) - ALLOWED_KEYS)
    if unknown:
        raise LayerError(f"{where}: unknown key(s) {', '.join(unknown)}")
    if data["kind"] != kind_dir or data["id"] != path.stem:
        raise LayerError(f"{where}: kind/id must match its folder and file name")
    if data["kind"] not in KIND_ORDER:
        raise LayerError(f"{where}: unknown kind '{data['kind']}'")
    fmt = data["profile_format"]
    if not isinstance(fmt, int) or fmt < 1:
        raise LayerError(f"{where}: profile_format must be a whole number")
    if fmt > SUPPORTED_FORMAT:
        raise LayerError(f"{where}: needs a newer scaffolder (layer format {fmt}, this tool reads up to {SUPPORTED_FORMAT})")
    bad = sorted(set(data.get("security", {})) - SECURITY_KEYS)
    if bad:
        raise LayerError(f"{where}: unknown security key(s) {', '.join(bad)}")
    contributions = data.get("json_merge", {})
    if not isinstance(contributions, dict):
        raise LayerError(f"{where}: json_merge must be a table of file paths to objects")
    for target, value in contributions.items():
        if not isinstance(value, dict):
            raise LayerError(f"{where}: json_merge '{target}' must be an object")
    for role, spec in data.get("roles", {}).items():
        if role not in ROLES:
            raise LayerError(f"{where}: unknown role '{role}'")
        if spec is False:
            continue
        if not isinstance(spec, dict) or spec.get("origin") not in ORIGINS or not isinstance(spec.get("path"), str):
            raise LayerError(f"{where}: role '{role}' needs path and origin ({', '.join(ORIGINS)}), or false")
    return Layer(data["kind"], data["id"], data["label"], str(data["version"]), data)


def load_catalog(layers_dir=LAYERS_DIR):
    """Return {'kind:id': Layer} for every layer file."""
    catalog = {}
    for kind_dir in sorted(p for p in Path(layers_dir).iterdir() if p.is_dir()):
        for f in sorted(kind_dir.glob("*.toml")):
            layer = _load_one(f, kind_dir.name)
            catalog[layer.ref] = layer
    if "base:base" not in catalog:
        raise LayerError("layers/base/base.toml is missing")
    return catalog


def layers_of(catalog, kind, include_hidden=False):
    return [l for l in catalog.values() if l.kind == kind and (include_hidden or not l.hidden)]


def requirement_met(req, selected_refs):
    """req is 'kind:id', 'kind:*', or alternatives joined by '|'."""
    for alt in req.split("|"):
        kind, _, ident = alt.strip().partition(":")
        if ident == "*":
            if any(r.startswith(kind + ":") for r in selected_refs):
                return True
        elif f"{kind}:{ident}" in selected_refs:
            return True
    return False
