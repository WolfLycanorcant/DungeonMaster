@echo off

:: Install requirements
python -m pip install -r requirements.txt

:: Run the Flask app from Server directory
python Server/main.py
