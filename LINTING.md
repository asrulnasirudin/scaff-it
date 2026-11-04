# Code checks

Ruff is installed in a separate `.venv-lint` environment. Application dependencies and source files are unchanged.

Scope: Repository Python code using its existing Ruff rules.

```powershell
python -m venv .venv-lint
.venv-lint/Scripts/python.exe -m pip install -r requirements-lint.txt
.venv-lint/Scripts/python.exe -m ruff check . --extend-exclude .venv-lint
```

The check reports existing issues without fixing them. It does not execute the application or validate Blender/Adobe host behavior.
