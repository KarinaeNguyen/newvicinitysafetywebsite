@echo off
REM Batch file to run weekly financial dashboard export
REM Can be scheduled via Windows Task Scheduler

setlocal enabledelayedexpansion

REM Get the directory this script is in
for %%I in ("%~dp0.") do set "SCRIPT_DIR=%%~fI"
set "BASE_DIR=%SCRIPT_DIR%\.."

REM Activate virtual environment
echo [%date% %time%] Starting financial dashboard export...
call "%BASE_DIR%\.venv\Scripts\activate.bat"

REM Run PowerShell script
echo [%date% %time%] Running export and commit...
powershell -ExecutionPolicy Bypass -File "%SCRIPT_DIR%\publish-dashboard.ps1"

if %errorlevel% equ 0 (
    echo [%date% %time%] SUCCESS: Dashboard exported and committed to GitHub
    exit /b 0
) else (
    echo [%date% %time%] ERROR: Dashboard export failed
    exit /b 1
)
