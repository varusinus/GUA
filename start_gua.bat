@echo off
title GUA - General Universal Agent
cd /d "%~dp0"
echo ============================================
echo   Starting GUA (General Universal Agent)
echo ============================================
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)

echo Checking dependencies...
python -m pip install -r requirements.txt >nul 2>nul

echo Signing the ruleset with your local key...
python governance\sign_ruleset.py --generate-key >nul 2>nul
python governance\verify_ruleset.py >nul 2>nul || (
  echo [!] Ruleset signature invalid - re-signing...
  python governance\sign_ruleset.py >nul 2>nul
)
python governance\verify_ruleset.py >nul 2>nul && (echo Ruleset: VALID and signed.) || (echo [!] WARNING: ruleset still invalid - GUA will refuse all requests.)

REM --- pick the best model: gua-self (feedback-trained) > gua-smart (7B) > gua-ft > gua > llama3.2 ---
REM Later lines win, so list them weakest-to-strongest.
set GUA_MODEL_NAME=llama3.2
ollama list | findstr /i /c:"gua:" >nul && set GUA_MODEL_NAME=gua
ollama list | findstr /i /c:"gua-ft" >nul && set GUA_MODEL_NAME=gua-ft
ollama list | findstr /i /c:"gua-smart" >nul && set GUA_MODEL_NAME=gua-smart
ollama list | findstr /i /c:"gua-self" >nul && set GUA_MODEL_NAME=gua-self
echo Using model: %GUA_MODEL_NAME%

set GUA_USE_NETWORK=1
set GUA_NODES=1

REM --- stop any old GUA servers so the new one actually takes over ---
echo Stopping any previous GUA servers...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8754 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul

echo Starting the web interface and the model bridge...
start "GUA web" cmd /c "python -m http.server 8000 --directory webui"
start "GUA bridge" cmd /c "python webui\backend\server.py"
timeout /t 4 >nul
start "" http://127.0.0.1:8000/index.html
echo.
echo GUA is running with model: %GUA_MODEL_NAME%
echo (Refresh the browser with Ctrl+Shift+R if it doesn't update.)
echo To stop GUA, close the "GUA web" and "GUA bridge" windows.
echo.
pause
