@echo off
chcp 65001 >nul
title Chatbot AI Lark
echo.
echo  ========================================
echo   CHATBOT AI LARK - Khoi dong...
echo  ========================================
echo.

cd /d "%~dp0"

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python chua duoc cai dat!
    echo    Tai Python tai: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if requirements are installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [*] Dang cai dat thu vien...
    pip install -r requirements.txt
)

REM Check if .env exists
if not exist ".env" (
    echo [!] File .env chua ton tai!
    echo    Copy config.env thanh .env va dien thong tin API keys
    copy config.env .env
    echo.
    echo [*] Vui long chinh sua file .env roi chay lai script nay!
    pause
    exit /b 1
)

REM Start the bot
echo [*] Khoi dong Chatbot AI Lark...
echo    Di den: http://localhost:5000
echo    Webhook: http://localhost:5000/webhook/lark
echo.
python main.py

pause
