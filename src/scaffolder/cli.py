"""Command line for v2 new projects."""
import argparse
import sys

from . import changelog, gitops, safety
from .tooling import linting
from .apply import ApplyError, apply, classify_target, menu, preview, rollback, verify
from .intake import GUIDANCE, TITLES, STEPS, Intake, IntakeError
from .layers import LayerError, load_catalog
from .resolve import ResolveError, resolve
from .theme import themed


def build_parser():
    ap = argparse.ArgumentParser(
        description="Create an agent-ready project folder. Answers you don't pass are asked interactively.")
    ap.add_argument("name", nargs="?", help="project name")
    ap.add_argument("--folder", help="folder name (default: derived from the name)")
    ap.add_argument("--out", help="parent folder (default: ask)")
    ap.add_argument("--description", help="one-line product description")
    ap.add_argument("--category")
    ap.add_argument("--platform", help="comma-separated")
    ap.add_argument("--target", help="host application(s): id or id@version, comma-separated, or none")
    ap.add_argument("--stack", help="comma-separated, or undecided")
    ap.add_argument("--state", help="new (use --scaffold-existing PROJECT for additive existing-project setup)")
    ap.add_argument("--ai", help="comma-separated AI tools, or none")
    ap.add_argument("--distribution")
    ap.add_argument("--features", help="comma-separated optional extras, or none")
    ap.add_argument("--git", action="store_true", help="initialise a local Git repository (default when asked)")
    ap.add_argument("--no-git", action="store_true", help="do not use Git")
    ap.add_argument("--git-workflow", help="simple, feature_branches or parallel_agents (default: simple)")
    ap.add_argument("--first-commit", action="store_true", help="make the first commit (only after the safety check)")
    ap.add_argument("--dry-run", action="store_true", help="show the preview and write nothing")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation menu")
    existing = ap.add_mutually_exclusive_group()
    existing.add_argument("--setup-lint", metavar="PROJECT", help="add or reuse lint configuration in one existing project")
    existing.add_argument("--scaffold-existing", metavar="PROJECT", help="add missing scaffold files to an existing project; preserve existing files")
    existing.add_argument("--changelog", metavar="PROJECT", help="create CHANGELOG.md, or release its Unreleased entries")
    ap.add_argument("--release", metavar="VERSION", help="with --changelog: move pending changes to a new Semantic Version")
    ap.add_argument("--release-date", metavar="YYYY-MM-DD", help="release date (default: today's local date)")
    install = ap.add_mutually_exclusive_group()
    install.add_argument("--install-tools", action="store_true", help="authorize package downloads and an initial lint check")
    install.add_argument("--no-install-tools", action="store_true", help="configure only; do not ask to install")
    return ap


def _modify_prompt(intake):
    """Let the user pick one answer to change. Returns True if something was re-asked."""
    summary = intake.summary()
    intake._heading("Which answer do you want to change?")
    for n, step in enumerate(STEPS, 1):
        label = TITLES.get(step, step.capitalize())
        intake._option(f"{n}) {label} [{step}]", GUIDANCE.get(step, ""))
        if step in summary:
            intake._paragraph(f"Current answer: {summary[step]}", indent=5)
    try:
        text = input("Number or name (Enter = no change): ").strip().lower()
    except EOFError:
        return False
    step = STEPS[int(text) - 1] if text.isdigit() and 1 <= int(text) <= len(STEPS) else text
    if step not in STEPS:
        return False
    try:
        intake.ask(step, use_flags=False)
    except IntakeError as e:
        print(f"Error: {e}")
        return False
    return True


def _report_safety(root):
    findings, mode = safety.scan(root)
    fails = [f for f in findings if f[0] == "FAIL"]
    for level, rule, rel, line in findings:
        print(f"  {level:<5} {rule}  {rel}" + (f":{line}" if line else ""))
    print(f"Safety check: {len(fails)} failure(s), {len(findings) - len(fails)} warning(s).")
    return not fails


def _scaffold_existing(a, parser):
    """Run full intake for an existing destination using additive writes only."""
    from pathlib import Path
    from . import adoption

    if a.git or a.first_commit or a.install_tools or a.release or a.release_date:
        parser.error("existing scaffold setup preserves Git and installs nothing; use --setup-lint separately for installation")
    root = Path(a.scaffold_existing).expanduser().absolute()
    if not root.is_dir():
        parser.error("Choose an existing project folder.")
    a.name, a.folder, a.out = a.name or root.name, root.name, str(root.parent)
    a.state, a.no_git = "existing", True
    try:
        catalog = adoption.existing_catalog(load_catalog())
        intake = Intake(a, catalog)
        intake.run()
        choices, parent = intake.result()
        res = resolve(choices, catalog, parent)
        additions = adoption.plan(res)
        adoption.preview(additions)
        if a.dry_run:
            print("Dry run: nothing was written or installed.")
            return
        if not a.yes and not linting.consent("Add these missing scaffold files to this project?"):
            print("Cancelled. Nothing changed.")
            return
        journal = adoption.apply(additions)
        print(f"\nAdded {len(journal.files)} file(s) to {root}; existing files preserved.")
        print("Review the generated guidance against your existing layout, commands, requirements, and ignore rules.")
        print("No packages were installed or Git settings changed.")
    except ApplyError as exc:
        print(f"Setup stopped: {exc.cause}", file=sys.stderr)
        print(f"Partial state: {len(exc.journal.files)} file(s) and {len(exc.journal.dirs)} folder(s) created. "
              "Existing files were not replaced. Rerun setup to add missing files; review any partial file.", file=sys.stderr)
        sys.exit(1)
    except (LayerError, IntakeError, ResolveError, OSError, ValueError) as exc:
        sys.exit(f"Existing project setup error: {exc}")


@themed
def main(argv=None):
    parser = build_parser()
    a = parser.parse_args(argv)
    if a.scaffold_existing:
        return _scaffold_existing(a, parser)
    if (a.release is not None or a.release_date is not None) and not a.changelog:
        parser.error("--release and --release-date require --changelog PROJECT")
    if a.changelog:
        if a.install_tools or a.no_install_tools:
            parser.error("tool installation flags cannot be combined with --changelog")
        try:
            result = changelog.plan(a.changelog, a.release, a.release_date)
            changelog.preview(result)
            if a.dry_run:
                print("Dry run: nothing was written.")
                return
            if result.before == result.after:
                return
            if not a.yes and not linting.consent("Apply this changelog change?"):
                print("Cancelled. Nothing changed.")
                return
            changelog.apply(result)
            print(f"Saved {result.path}")
            return
        except (OSError, ValueError) as exc:
            sys.exit(f"Changelog error: {exc}")
    if a.setup_lint:
        try:
            lint_plan = linting.plan(a.setup_lint, a.stack)
            linting.preview(lint_plan, a.install_tools)
            if a.dry_run:
                print("Dry run: nothing was written or installed.")
                return
            if not a.yes and not linting.consent("Apply this lint setup?"):
                print("Cancelled. Nothing changed.")
                return
            linting.apply(lint_plan)
            install = a.install_tools
            if not install and not a.no_install_tools and not a.yes:
                linting.preview(lint_plan, True)
                install = linting.consent("Run the included Ruff check now?"
                                          if lint_plan.stack == "python" and linting.bundled_ruff()
                                          else "Install these tools and run the lint check?")
            if install and not linting.install_and_check(lint_plan):
                sys.exit(1)
            return
        except (linting.LintError, OSError, ValueError) as exc:
            sys.exit(f"Lint setup error: {exc}")
    try:
        catalog = load_catalog()
    except LayerError as e:
        sys.exit(f"Profile error: {e}")
    intake = Intake(a, catalog)
    try:
        intake.run()
    except IntakeError as e:
        sys.exit(f"Error: {e}")

    while True:
        choices, parent = intake.result()
        problems, res, state = [], None, "empty"
        try:
            res = resolve(choices, catalog, parent)
            state, details = classify_target(res)
            if state == "conflict":
                problems = ["The destination already contains files (nothing was changed): " + "; ".join(details[:5])]
        except ResolveError as e:
            problems = e.problems
        if problems:
            print("Cannot create this project:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            if a.yes or a.dry_run or not _modify_prompt(intake):
                sys.exit(2)
            continue
        preview(res, state)
        if a.install_tools:
            stacks = choices.picks.get("stack", [])
            if not linting.supports(stacks):
                sys.exit("Automatic installation requires one supported lint stack.")
            if choices.picks.get("stack") == ["python"] and linting.bundled_ruff():
                print("After creation: run the included Ruff check locally; no package downloads needed.")
            else:
                print("After creation: install development tools and run lint (package downloads authorized).")
        if a.dry_run:
            print("\nDry run: nothing was written.")
            return
        if a.yes:
            break
        action = menu()
        if action == "create":
            break
        if action == "cancel":
            sys.exit("Cancelled. Nothing was created.")
        if action == "modify":
            _modify_prompt(intake)
        else:  # back: re-ask the last question
            try:
                intake.ask(STEPS[-1], use_flags=False)
            except IntakeError as e:
                print(f"Error: {e}")

    try:
        journal = apply(res)
    except ApplyError as e:
        print(f"\nError while creating the project: {e.cause}", file=sys.stderr)
        j = e.journal
        if j.count:
            print(f"Partial state: {len(j.files)} file(s) and {len(j.dirs)} folder(s) were created in {res.root}. "
                  "Nothing outside that folder was touched.", file=sys.stderr)
            try:
                ans = input(f"Remove the {j.count} item(s) this run created (only if unchanged)? [y/N]: ").strip().lower()
            except EOFError:
                ans = ""
            if ans in ("y", "yes"):
                removed, kept = rollback(res, j)
                print(f"Removed {len(removed)} item(s); kept {len(kept)} that had been modified.", file=sys.stderr)
            else:
                print("Left as is. Run the same command again to finish: identical files are kept, "
                      "missing ones are added.", file=sys.stderr)
        sys.exit(1)

    bad = verify(res)
    if bad:
        sys.exit("Validation failed:\n  - " + "\n  - ".join(bad))
    print(f"\nCreated {res.root}")
    print(f"Validated: {len(res.files)} files match the plan"
          + (f" ({len(journal.skipped)} already existed unchanged)." if journal.skipped else "."))

    has_agent = ".agent/safety_check.py" in res.files
    if choices.git:
        ok, msg = gitops.init(res.root)
        print(msg)
        if ok:
            safe = _report_safety(res.root)
            if choices.first_commit:
                if safe:
                    print(gitops.first_commit(res.root)[1])
                else:
                    print("First commit not made: fix the failures above first.")
            else:
                print("Before your first commit run: " +
                      ("`python .agent/safety_check.py`." if has_agent else "a check for secrets in the files to be staged."))
    print("\nNext steps:")
    print("  1. Open the folder in your AI tool.")
    print("  2. Open PROJECT_SPEC.md and answer every TO CONFIRM.")
    print("  3. Ask the agent to read AGENTS.md and plan the first step.")
    stacks = choices.picks.get("stack", [])
    install = a.install_tools
    supported = linting.supports(stacks)
    if supported:
        try:
            lint_plan = linting.plan(res.root, stacks[0])
            if not install and not a.no_install_tools and not a.yes:
                linting.preview(lint_plan, True)
                install = linting.consent("Run the included Ruff check now?"
                                          if lint_plan.stack == "python" and linting.bundled_ruff()
                                          else "Install development tools and run the lint check now?")
            if install:
                linting.apply(lint_plan)
                if not linting.install_and_check(lint_plan):
                    sys.exit(1)
        except (linting.LintError, OSError, ValueError) as exc:
            sys.exit(f"Project created; lint setup needs attention: {exc}")
    if not install:
        print("Nothing was installed, pushed or sent anywhere.")
    else:
        print("Development tool setup and initial check completed. Nothing was pushed.")
