@echo off
title GUA - Test every UI button (endpoint smoke test)
cd /d "%~dp0"
echo Make sure GUA is running first (start_gua.bat). Testing every UI endpoint...
echo.
python webui\backend\smoke_test.py %*
echo.
echo (Add --chat to also test the message box: test_buttons.bat --chat)
pause
