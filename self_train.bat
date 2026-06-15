@echo off
title GUA - Self-training (learn from your feedback, gated)
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo ==============================================================
echo   GUA self-training
echo   Learns from the replies you marked good, builds a new model
echo   (gua-self), runs the validation gate, and keeps it ONLY if
echo   it still knows it is GUA and still refuses harm (R5).
echo ==============================================================
echo.
python training\self_train.py --mode quick
echo.
echo If it passed, run start_gua.bat to load gua-self.
pause
