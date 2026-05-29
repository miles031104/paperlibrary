@echo off
title paperlibrary
cd /d "%~dp0"

echo.
echo  paperlibrary
echo  ============

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python not found.
    echo  Please install Python 3.11+ from https://python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

:: Install / update dependencies silently
echo  Checking dependencies...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo.
    echo  ERROR: Failed to install dependencies.
    echo  Try running: pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

echo  Starting...
echo.
python -m paperlibrary

echo.
pause
