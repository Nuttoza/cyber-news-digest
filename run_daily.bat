@echo off
chcp 65001 >nul
echo ===================================================
echo  Starting Cyber Threat Intelligence Daily Digest...
echo ===================================================
cd /d "%~dp0"
python main.py
echo.
echo Process finished. Check the "output" folder for .docx and .pdf reports.
pause
