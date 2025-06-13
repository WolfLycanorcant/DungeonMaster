@echo off
:: Activate Python virtual environment and start the game server

:: Change to the script's directory
cd /d %~dp0

:: Define the virtual environment directory name
set VENV_DIR=venv

:: Check if virtual environment exists, if not create it
if not exist "%VENV_DIR%" (
    echo Creating new virtual environment...
    python -m venv %VENV_DIR%
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment
        pause
        exit /b 1
    )
    
    echo Installing required packages...
    call %VENV_DIR%\Scripts\activate.bat
    pip install -r requirements.txt
    
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to install required packages
        pause
        exit /b 1
    )
    
    echo Environment created and packages installed successfully!
) else (
    :: Activate existing virtual environment
    call %VENV_DIR%\Scripts\activate.bat
)

:: Start the Flask server
echo Starting Dungeon Master server...
python Server/app.py

:: Keep the window open if there's an error
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Server stopped with error. Press any key to exit...
    pause >nul
)
