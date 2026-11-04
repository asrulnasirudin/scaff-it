# Scaff It code checks

Scope: maintained Scaff It source, tests, templates, and build tooling only.
Run Ruff with the repository's ruff.toml, followed by unittest, readiness, and
repository safety checks. See the developer guide for commands.

Existing-project lint setup preserves recognized user configuration, requires
separate consent for downloads, and reports failures without automatic source fixes.
Passing lint does not establish runtime security or Windows release acceptance.
