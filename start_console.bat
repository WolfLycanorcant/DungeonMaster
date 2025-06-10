@echo off

:: Activate the virtual environment
call dungeonmaster\Scripts\activate.bat

:: Install requirements if not already installed
if not exist "dungeonmaster\Lib\site-packages\dotenv" (
    pip install -r requirements.txt
)

:: Run the main game
python main.py

:: Keep the console window open after the game ends
pause
