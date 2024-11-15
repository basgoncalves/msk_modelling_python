@echo off
cd %~dp0
echo "Running main.py"
python --version
python .\main.py
if %errorlevel% neq 0 (
    echo "Error: Failed to run main.py"
    pause
)