@echo off
title GUA - Clean-clone verification
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo Installing dependencies into THIS Python (python -m pip)...
python -m pip install -r requirements.txt
echo.
python verify.py
echo.
echo ================================================================
echo  Result above is also saved to verify_report.txt in this folder.
echo ================================================================
echo.
echo This window will stay open. Read the result, then type EXIT to close.
cmd /k
