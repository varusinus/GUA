@echo off
title GUA - Resilience demo (kill a node, keep the model)
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo ==============================================================
echo   GUA resilience demo
echo   Shows: the model is replicated across nodes, so a node
echo   hitting its kill-switch never loses it. Only losing EVERY
echo   replica at once loses the model.
echo ==============================================================
echo.
python network\replication_demo.py
echo.
pause
