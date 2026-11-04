@echo off
setlocal
title Scaff It
py -3 -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
if not errorlevel 1 (
    py -3 "%~dp0src\project_scaffolder.py"
) else (
    python -c "import sys; sys.exit(sys.version_info < (3, 11))" >nul 2>nul
    if not errorlevel 1 (
        python "%~dp0src\project_scaffolder.py"
    ) else (
        echo Python 3.11 or newer is needed. Install Python, then run this file again.
    )
)
echo.
pause
