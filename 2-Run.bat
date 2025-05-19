@echo off
echo ===================================================
echo Claude Desktop Pilot - STEP 2: RUN APPLICATION
echo ===================================================
echo.

REM Check if virtual environment exists
if not exist .venv (
    echo ERROR: Virtual environment not found!
    echo.
    echo Please run the installation first by double-clicking:
    echo "1-Install.bat"
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Start the application
echo Starting Claude Desktop Pilot...
echo The application will open in your default browser.
echo.
echo Press Ctrl+C in this window to stop the application when you're done.
echo.
streamlit run app.py

REM Deactivate virtual environment on exit
call .venv\Scripts\deactivate.bat 