@echo off
echo ============================================
echo Vicinity Safety Financial Management System
echo ============================================
echo.

REM Resolve app root and activate virtual environment
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "APP_DIR=%%~fI"
call "%APP_DIR%\.venv\Scripts\activate.bat"

REM Launch the application
echo Starting Financial System UI...
python "%APP_DIR%\app\finance_ui.py"

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo An error occurred. Press any key to exit...
    pause > nul
)
