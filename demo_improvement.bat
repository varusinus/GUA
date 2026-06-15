@echo off
title GUA - Federated self-improvement demo
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo ==============================================================
echo   GUA federated self-improvement
echo   Three nodes pool their thumbs-up feedback as SIGNED
echo   improvements. After they gossip, every node holds the whole
echo   network's verified training set - so more nodes = smarter.
echo   Tampered improvements are rejected.
echo ==============================================================
echo.
python network\improvement_demo.py
echo.
pause
