@echo off
REM Vicinity Safety - Financial UI Launcher
REM Launch the financial management system; fall back with visible errors if needed.

setlocal
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "APP_DIR=%%~fI"
set "APP=%APP_DIR%\app\finance_ui.py"
set "VENV_PYTHONW=%APP_DIR%\.venv\Scripts\pythonw.exe"
set "VENV_PYTHON=%APP_DIR%\.venv\Scripts\python.exe"
set "LOG=%APP_DIR%\launch\launch_finance_ui.log"

cd /d "%APP_DIR%" || (
	echo Failed to access %APP_DIR%.
	pause
	exit /b 1
)

if exist "%VENV_PYTHONW%" (
	REM Use pythonw for a hidden window. Log start time for troubleshooting.
	echo [%DATE% %TIME%] Starting UI with pythonw.>>"%LOG%"
	start "" "%VENV_PYTHONW%" "%APP%"
	exit /b 0
)

if exist "%VENV_PYTHON%" (
	echo [%DATE% %TIME%] pythonw.exe missing. Falling back to python.exe.>>"%LOG%"
	echo pythonw.exe not found. Starting with python.exe so errors are visible.
	"%VENV_PYTHON%" "%APP%"
	if errorlevel 1 (
		echo.
		echo The UI failed to start. Check %LOG% for details.
		pause
		exit /b 1
	)
	exit /b 0
)

echo [%DATE% %TIME%] Virtual environment not found at %APP_DIR%\.venv.>>"%LOG%"
echo Virtual environment not found at %APP_DIR%\.venv.
echo Run the setup script or reinstall dependencies.
pause
exit /b 1
