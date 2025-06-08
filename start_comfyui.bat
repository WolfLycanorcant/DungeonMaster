@echo off
REM Batch file to start the ComfyUI Image Generator

echo Starting ComfyUI Image Generator...
echo ===================================

REM Change to the ComfyUI directory
cd /d "C:\Users\wolfl\Documents\ComfyUI"

REM Run the image generator
python run_image_generator.py

REM Keep the window open to see any error messages
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Press any key to exit...
    pause >nul
) else (
    timeout /t 3 >nul
)