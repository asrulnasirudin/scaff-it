"""INTAKE: turn flags and menu answers into Choices. Menus are generated from the layer catalog.

Every step can be answered by a command-line option or interactively, and can be asked again
later (Modify/Back in the preview). Each answer remembers where it came from:
user (typed or passed), default (accepted a default), inferred, detected.
"""
import sys
import shutil
import textwrap

from .layers import layers_of, requirement_met
from .resolve import Choices, default_folder, git_workflows

STEPS = ("name", "location", "description", "category", "platform", "target", "stack", "state",
         "ai", "distribution", "features", "git")
KIND_STEPS = {"category": "category", "platform": "platform", "target": "target", "stack": "stack",
              "state": "state", "ai": "ai", "distribution": "distribution"}
MULTI = {"platform", "target", "stack", "ai"}
TITLES = {"category": "Project category", "platform": "Platform(s)", "target": "Host application(s)",
          "stack": "Technology stack", "state": "Project state", "ai": "AI coding tools",
          "distribution": "Distribution (how it is delivered)"}
NONE_WORD = {"stack": "undecided", "target": "none", "ai": "none", "platform": "none"}
GUIDANCE = {
    "name": "What would you like to call this project? Its folder name is based on this answer.",
    "location": "The parent folder is where the new project folder will be created.",
    "description": "Describe what you are making in one short sentence, or leave it blank for now.",
    "category": "What kind of project are you making? Choose the closest match.",
    "platform": "Where will people use the finished project? You can choose more than one.",
    "target": "A host application is another program your project runs inside. A standalone project can use none.",
    "stack": "A technology stack is the set of languages and tools used to build your project. If you are unsure, choose undecided; nothing is installed here.",
    "state": "This creation workflow starts a new project. To add missing scaffolding to an existing project, choose that option in the main launcher.",
    "ai": "Which coding assistants will you use? This adds project instructions for them. You can choose more than one, or none.",
    "distribution": "How do you expect to share the finished project? This records the plan; it does not build or publish anything.",
    "features": "Optional folders and guidance for working files, private settings, or feedback from testers.",
    "git": "Choose whether to keep local change history, how work is organized, and whether to save a first snapshot.",
}
NONE_GUIDANCE = {
    "stack": "Decide the languages and tools later; no technology-specific setup is chosen.",
    "target": "This project does not run inside another program.",
    "ai": "Do not add instructions for a particular coding assistant.",
    "platform": "Leave the intended devices or operating systems unspecified for now.",
}
WORKFLOW_GUIDANCE = {
    "simple": "Work in one main copy and save small, checked changes. A straightforward choice when working on your own.",
    "feature_branches": "Give each task its own line of changes (a branch), then combine it with the main version after checking it.",
    "parallel_agents": "Give each coding assistant its own line of changes and preferably its own working folder, so they can work at the same time.",
}


class IntakeError(Exception):
    pass


def _ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        raise IntakeError(f"No answer available for: {prompt.strip()} (pass it as a command-line option)")


def _ask_optional(prompt, default=""):
    """Ask, but quietly use the default when no input is available (non-interactive runs)."""
    try:
        return input(prompt).strip()
    except EOFError:
        return default


def _yes_no(prompt, default, out):
    suffix = " [Y/n]: " if default else " [y/N]: "
    while True:
        try:
            text = input(prompt + suffix).strip().lower()
        except EOFError:
            return default, "default"
        if not text:
            return default, "default"
        if text in ("y", "yes"):
            return True, "user"
        if text in ("n", "no"):
            return False, "user"
        print("Please answer y or n.", file=out)


def _truthy(text):
    return text.strip().lower() in ("y", "yes", "true", "1", "on")


class Intake:
    def __init__(self, args, catalog, out=None):
        self.a, self.cat, self.out = args, catalog, out or sys.stdout
        self.name = self.folder = self.parent = None
        self.description = ""
        self.picks, self.versions, self.sources = {}, {}, {}
        self.git, self.git_workflow, self.first_commit = True, "simple", False
        self.flags = {"category": args.category, "platform": args.platform, "target": args.target,
                      "stack": args.stack, "state": args.state, "ai": args.ai,
                      "distribution": args.distribution}

    def _paragraph(self, text: str, indent: int = 2) -> None:
        width = max(20, min(88, shutil.get_terminal_size(fallback=(88, 24)).columns - 2))
        padding = " " * indent
        print(textwrap.fill(text, width=width, initial_indent=padding,
                            subsequent_indent=padding), file=self.out)

    def _heading(self, title: str, step: str | None = None) -> None:
        width = max(20, min(88, shutil.get_terminal_size(fallback=(88, 24)).columns - 2))
        print("\n\n" + "=" * width, file=self.out)
        if step is not None:
            self._paragraph(f"QUESTION {STEPS.index(step) + 1} OF {len(STEPS)}", indent=0)
        self._paragraph(title, indent=0)
        print("=" * width + "\n", file=self.out)

    def _option(self, label: str, description: str) -> None:
        print(file=self.out)
        self._paragraph(label)
        if description:
            self._paragraph(description, indent=5)

    # ---- running -------------------------------------------------------
    def run(self):
        for step in STEPS:
            self.ask(step, use_flags=True)

    def ask(self, step, use_flags=False):
        if step in KIND_STEPS:
            self._step_kind(step, use_flags)
        else:
            getattr(self, f"_step_{step}")(use_flags)

    def result(self):
        return (Choices(name=self.name.strip(), folder=self.folder, picks=self.picks, versions=self.versions,
                        sources=dict(self.sources), git=self.git, git_workflow=self.git_workflow,
                        first_commit=self.first_commit, description=self.description), self.parent)

    def summary(self):
        """Current answers, for the Modify menu."""
        labels = lambda kind: ", ".join(self.picks.get(kind, [])) or "(none)"
        return {
            "name": self.name, "location": self.parent, "description": self.description or "(none)",
            "category": labels("category"), "platform": labels("platform"), "target": labels("target"),
            "stack": labels("stack") if self.picks.get("stack") else "undecided",
            "state": labels("state"), "ai": labels("ai"), "distribution": labels("distribution"),
            "features": labels("feature"),
            "git": (f"yes, {self.git_workflow}" + (", first commit" if self.first_commit else "")) if self.git else "no",
        }

    # ---- simple steps --------------------------------------------------
    def _step_name(self, use_flags):
        if use_flags and self.a.name:
            self.name, self.sources["name"] = self.a.name, "user"
        else:
            self._heading("Project name", "name")
            self._paragraph(GUIDANCE["name"])
            self.name, self.sources["name"] = _ask("\nProject name: "), "user"
        if not self.name.strip():
            raise IntakeError("A project name is required.")
        if use_flags and self.a.folder:
            self.folder, self.sources["folder"] = self.a.folder, "user"
        else:
            self.folder, self.sources["folder"] = default_folder(self.name), "default"

    def _step_location(self, use_flags):
        if use_flags and self.a.out is not None:
            self.parent = self.a.out
        else:
            self._heading("Project location", "location")
            self._paragraph(GUIDANCE["location"])
            self._paragraph("Press Enter to use the current folder.")
            self.parent = _ask("\nParent folder: ") or "."
        self.sources["location"] = "user"

    def _step_description(self, use_flags):
        if use_flags and self.a.description is not None:
            self.description = self.a.description
            self.sources["description"] = "user"
        else:
            self._heading("Project description", "description")
            self._paragraph(GUIDANCE["description"])
            self.description = _ask_optional("\nDescription (Enter to skip): ")
            self.sources["description"] = "user" if self.description else "default"

    # ---- menu steps ----------------------------------------------------
    def _plausible(self, layer):
        refs = {f"{k}:{i}" for k, ids in self.picks.items() for i in ids}
        asked = set(self.picks)
        for req in layer.data.get("requires", []):
            undecided = any(x.split(":")[0] not in asked for x in req.split("|"))
            if not undecided and not requirement_met(req, refs):
                return False
        for con in layer.data.get("conflicts", []):
            for alt in con.split("|"):
                kind, _, ident = alt.partition(":")
                if kind in asked and (any(r.startswith(kind + ":") for r in refs) if ident == "*" else alt in refs):
                    return False
        return True

    def _defaults(self, kind, options):
        ids = [o.id for o in options]
        rec = []
        for k, chosen in self.picks.items():
            for i in chosen:
                for r in self.cat[f"{k}:{i}"].data.get("recommends", []):
                    rk, _, ri = r.partition(":")
                    if rk == kind and ri in ids and ri not in rec:
                        rec.append(ri)
        if rec:
            return rec if kind in MULTI else rec[:1]
        flagged = [o.id for o in options if o.data.get("default")]
        return flagged[:1] if flagged else []

    def _parse(self, text, options, multi):
        by_id = {o.id: o.id for o in options}
        result = []
        for tok in [t.strip() for t in text.replace(" ", ",").split(",") if t.strip()]:
            if multi and tok.lower() in ("0", "none", "undecided"):
                return []
            if tok.isdigit() and 1 <= int(tok) <= len(options):
                ident = options[int(tok) - 1].id
            elif tok.lower() in by_id:
                ident = tok.lower()
            else:
                raise IntakeError(f"'{tok}' is not one of the choices.")
            if ident not in result:
                result.append(ident)
        if not multi and len(result) != 1:
            raise IntakeError("Choose exactly one.")
        return result

    def _from_flag(self, kind, flag):
        if kind == "target":
            ids = []
            for tok in flag.split(","):
                tok = tok.strip()
                if not tok or tok.lower() == "none":
                    continue
                ident, _, ver = tok.partition("@")
                ids.append(ident.lower())
                if ver:
                    self.versions[f"target:{ident.lower()}"] = ver
            return ids
        if kind in MULTI and flag.strip().lower() in ("none", "undecided"):
            return []
        return [t.strip().lower() for t in flag.split(",") if t.strip()]

    def _step_kind(self, kind, use_flags):
        flag = self.flags[kind] if use_flags else None
        if flag is not None:
            self.picks[kind], self.sources[kind] = self._from_flag(kind, flag), "user"
        else:
            self._menu_step(kind)
        if kind == "target":
            for ident in self.picks.get("target", []):
                ref = f"target:{ident}"
                layer = self.cat.get(ref)
                if layer and layer.data.get("ask_version") and ref not in self.versions:
                    self._heading(f"{layer.label}: version")
                    self._paragraph("Use the version number shown in the program's About screen. Leave it blank if you do not know it.")
                    self.versions[ref] = _ask_optional(
                        "\nVersion (e.g. 5.2; Enter to skip): ")

    def _menu_step(self, kind):
        out = self.out
        options = [l for l in layers_of(self.cat, kind) if self._plausible(l)]
        multi = kind in MULTI
        defaults = self._defaults(kind, options)
        needs_target = kind == "target" and any(
            r.startswith("target:") for i in self.picks.get("category", [])
            for r in self.cat[f"category:{i}"].data.get("requires", []))
        if not options:
            self.picks[kind], self.sources[kind] = [], "default"
            return
        if len(options) == 1 and not multi and defaults:
            self.picks[kind], self.sources[kind] = [options[0].id], "default"
            return
        self._heading(TITLES[kind], kind)
        self._paragraph(GUIDANCE[kind])
        for n, o in enumerate(options, 1):
            mark = "  (default)" if o.id in defaults else ""
            self._option(f"{n}) {o.label} [{o.id}]{mark}", o.data.get("description", ""))
        none_word = NONE_WORD.get(kind, "none")
        if multi and not needs_target:
            self._option(f"0) {none_word.capitalize()}", NONE_GUIDANCE[kind])
        print(file=out)
        if defaults:
            default_names = ", ".join(o.label for o in options if o.id in defaults)
            self._paragraph(f"Press Enter to keep: {default_names}.")
        elif multi:
            if needs_target:
                self._paragraph("Choose at least one program; this project needs a host application.")
            else:
                self._paragraph(f"Press Enter for {none_word}.")
        else:
            self._paragraph("Choose one option; there is no default.")
        hint = ("numbers or ids, comma-separated; Enter = " + ("default" if defaults else none_word)) if multi \
            else "number or id; Enter = default"
        hint = hint.replace("ids", "names in brackets").replace("id;", "name in brackets;")
        if needs_target and not defaults:
            hint = "numbers or names in brackets, comma-separated; at least one required"
        elif not multi and not defaults:
            hint = "number or name in brackets"
        self._paragraph(f"Choose by {hint}.")
        prompt = "\nYour choice: "
        while True:
            text = _ask(prompt)
            if not text:
                if not multi and not defaults:
                    print("Please choose one.", file=out)
                    continue
                chosen, src = list(defaults), ("default" if defaults else "user")
            else:
                try:
                    chosen, src = self._parse(text, options, multi), "user"
                except IntakeError as e:
                    print(e, file=out)
                    continue
            if needs_target and not chosen:
                print("Please choose a host application.", file=out)
                continue
            self.picks[kind], self.sources[kind] = chosen, src
            return

    # ---- features and git ---------------------------------------------
    def _step_features(self, use_flags):
        options = layers_of(self.cat, "feature")
        if not options:
            self.picks["feature"], self.sources["features"] = [], "default"
            return
        flag = self.a.features if use_flags else None
        if flag is not None:
            ids = [] if flag.strip().lower() == "none" else [t.strip().lower() for t in flag.split(",") if t.strip()]
            self.picks["feature"], self.sources["features"] = ids, "user"
            return
        chosen, src = [], "default"
        self._heading("Optional extras", "features")
        self._paragraph("Each extra is optional. Yes adds it; No leaves it out. Press Enter for No.")
        for number, o in enumerate(options, 1):
            self._heading(f"OPTIONAL EXTRA {number} OF {len(options)}: {o.label}")
            self._paragraph(o.data.get("description", ""))
            ans, how = _yes_no("\nInclude this extra?", False, self.out)
            if ans:
                chosen.append(o.id)
            if how == "user":
                src = "user"
        self.picks["feature"], self.sources["features"] = chosen, src

    def _step_git(self, use_flags):
        a = self.a
        if use_flags and a.no_git:
            self.git, self.sources["git"] = False, "user"
        elif use_flags and (a.git_workflow or a.first_commit or a.git):
            self.git, self.sources["git"] = True, "user"
        else:
            self._heading("Git: local change history", "git")
            self._paragraph("Git keeps a history of changes on your computer. Yes prepares that history; No leaves Git out. Neither choice uploads your project.")
            self.git, self.sources["git"] = _yes_no("\nSet up Git?", True, self.out)
        workflows = git_workflows()
        if use_flags and a.git_workflow:
            self.git_workflow, self.sources["git_workflow"] = a.git_workflow, "user"
        elif self.git:
            self._heading("Git workflow")
            self._paragraph("How should future work be organized? This records instructions; it does not create branches or extra working folders.")
            for n, w in enumerate(workflows, 1):
                self._option(f"{n}) {w}" + ("  (default)" if w == "simple" else ""), WORKFLOW_GUIDANCE.get(w, ""))
            self._paragraph("Choose a number or name. Press Enter for simple.")
            text = _ask_optional("\nYour choice: ")
            if not text:
                self.git_workflow, self.sources["git_workflow"] = "simple", "default"
            else:
                pick = workflows[int(text) - 1] if text.isdigit() and 1 <= int(text) <= len(workflows) else text.lower()
                self.git_workflow, self.sources["git_workflow"] = pick, "user"
        else:
            self.git_workflow, self.sources["git_workflow"] = "simple", "default"
        if use_flags and a.first_commit:
            self.first_commit, self.sources["first_commit"] = True, "user"
        elif self.git:
            self._heading("Git: first saved snapshot")
            self._paragraph("A commit is a saved snapshot in Git history. Yes saves the generated files after checking them; No lets you review and save later. Enter means No.")
            self.first_commit, self.sources["first_commit"] = _yes_no(
                "\nSave the first snapshot now?", False, self.out)
        else:
            self.first_commit, self.sources["first_commit"] = False, "default"
