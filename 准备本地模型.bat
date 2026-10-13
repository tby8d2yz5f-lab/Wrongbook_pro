@echo off
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install it first from https://ollama.com/download/windows
  pause
  exit /b 1
)
echo Downloading qwen3-vl:8b (about 6.1 GB). This is the recommended quality option.
ollama pull qwen3-vl:8b
if errorlevel 1 (
  echo Download failed. Check that Ollama is running and try again.
) else (
  echo Model is ready. Next, double-click Start.
)
pause