@echo off
chcp 65001 >nul
cd /d "%~dp0"
python 更新网页.py
if errorlevel 1 pause
