@echo off
setlocal
cd /d "%~dp0"
set OLLAMA_MODEL=qwen3-vl:4b
set ZHI_CUO_LAN=1
where py >nul 2>nul
if not errorlevel 1 (
  py -3 server.py
  goto done
)
where python >nul 2>nul
if not errorlevel 1 (
  python server.py
  goto done
)
echo Python 3 was not found. Install Python 3, then run this file again.
echo https://www.python.org/downloads/windows/
pause
:done
endlocal
