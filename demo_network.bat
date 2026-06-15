@echo off
title GUA - Real two-node network (federation over TCP)
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Python not found. Install Python 3.10+ and retry. & pause & exit /b 1)
echo ==============================================================
echo   GUA real network demo - two nodes on this machine
echo   Node A seeds the model. Node B joins A and pulls it over
echo   real TCP. Close A's window (its kill-switch) and B keeps
echo   serving the model. This is the real daemon, not a sim.
echo ==============================================================
echo.
start "GUA node A (seed)"  cmd /k python network\node_daemon.py --id A --port 9401 --data .gua-node\A --seed-text "GUA model v1 (demo seed)" --key gua-model
timeout /t 3 >nul
start "GUA node B (joins A)" cmd /k python network\node_daemon.py --id B --port 9402 --data .gua-node\B --peers 127.0.0.1:9401
echo.
echo Two real node windows are open. Watch B pull 'gua-model' from A.
echo Then CLOSE node A's window and watch B keep the model.
echo.
pause
