@echo off
title Build GUA custom model
cd /d "%~dp0..\.."
echo Generating Modelfile from the GUA dataset...
python training\finetune\make_modelfile.py
echo Creating the "gua" model in Ollama (this bakes in GUA's identity)...
ollama create gua -f training\finetune\Modelfile
echo.
echo Done. A model named "gua" now exists.
echo Restart GUA with start_gua.bat - it will use "gua" automatically.
echo Then open the UI and click "Check + promote version" to bump to v2.
echo.
pause
