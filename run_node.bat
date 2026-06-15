@echo off
title GUA - Run a network node
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo ==============================================================
echo   GUA node - join the network and help keep the model alive
echo ==============================================================
echo.
echo Usage:
echo   run_node.bat                 (start a standalone node, port 9075)
echo   run_node.bat HOST:PORT       (join an existing node on the network)
echo.
echo Example to join a friend's node:
echo   run_node.bat 203.0.113.7:9075
echo (They must open/forward TCP port 9075 to be reachable over the internet.)
echo.
set PEER=%1
if "%PEER%"=="" (
  echo Starting a standalone node on port 9075 ...
  python network\node_daemon.py --id %COMPUTERNAME% --port 9075 --data .gua-node\local
) else (
  echo Starting a node on port 9075, joining %PEER% ...
  python network\node_daemon.py --id %COMPUTERNAME% --port 9075 --data .gua-node\local --peers %PEER%
)
pause
