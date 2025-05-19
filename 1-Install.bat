@echo off
echo ===================================================
echo Claude Desktop Pilot - STEP 1: INSTALL
echo ===================================================
echo.

REM Check if Python is installed
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed! Please install Python 3.8 or newer.
    echo You can download it from https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment!
        pause
        exit /b 1
    )
) else (
    echo Virtual environment already exists.
)

REM Activate virtual environment and install requirements
echo.
echo Installing required packages...
call .venv\Scripts\activate.bat
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo Failed to install requirements!
    pause
    exit /b 1
)

echo.
echo ===================================================
echo Installation completed successfully!
echo.
echo You can now run the application by double-clicking:
echo "2-Run.bat"
echo ===================================================
echo.
pause 