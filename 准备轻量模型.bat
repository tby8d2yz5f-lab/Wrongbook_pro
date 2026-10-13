@echo off
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama was not found. Install it first from https://ollama.com/download/windows
  pause
  exit /b 1
)
echo Downloading qwen3-vl:4b (about 3.3 GB). Choose this smaller model for limited PC resources.
ollama pull qwen3-vl:4b
if errorlevel 1 (
  echo Download failed. Check that Ollama is running and try again.
) else (
  echo Model is ready. Start with Start-Lightweight.
)
pause