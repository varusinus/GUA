@echo off
title GUA - Smarter brain
cd /d "%~dp0"
if "%GUA_SMART_BASE%"=="" set GUA_SMART_BASE=qwen2.5:7b
echo ==============================================================
echo   Building GUA on a bigger, smarter base: %GUA_SMART_BASE%
echo   (To use another, set GUA_SMART_BASE first, e.g.
echo    set GUA_SMART_BASE=llama3.1:8b   then run this again.)
echo ==============================================================
ollama list | findstr /i /c:"%GUA_SMART_BASE:~0,7%" >nul || (echo [!] %GUA_SMART_BASE% not found in Ollama. Run:  ollama pull %GUA_SMART_BASE%  & pause & exit /b 1)
cd training\finetune
python make_smart_gua.py || (echo [!] failed to write Modelfile & pause & exit /b 1)
cd ..\..
echo Importing the smarter GUA into Ollama as "gua-smart" ...
ollama create gua-smart -f training\finetune\Modelfile.smart || (echo [!] ollama create failed & pause & exit /b 1)
echo.
echo Done - "gua-smart" is built on a %GUA_SMART_BASE% brain (much smarter than the 3B).
echo Now run start_gua.bat - it auto-picks gua-smart.
echo.
pause
