@echo off
setlocal EnableExtensions
REM Lance API FastAPI (:8000) + UI Vite (:5173). Ferme cette fenetre pour arreter (ou Ctrl+C).

cd /d "%~dp0"

if exist .env (
  for /f "usebackq tokens=* eol=#" %%A in (".env") do (
    for /f "tokens=1* delims==" %%B in ("%%A") do (
      if not "%%B"=="" set "%%B=%%C"
    )
  )
)

where python >nul 2>&1
if errorlevel 1 (
  echo Python introuvable. Installe Python 3.10+.
  exit /b 1
)

where npm >nul 2>&1
if errorlevel 1 (
  echo npm introuvable. Installe Node.js 18+.
  exit /b 1
)

if not exist "web\node_modules\" (
  echo -^> Installation des deps web ^(npm install^)...
  pushd web
  call npm install
  popd
)

echo -^> API  http://127.0.0.1:8000
start "AgentAutonome-API" /D "%~dp0" cmd /k python -m uvicorn server.app:app --reload --host 127.0.0.1 --port 8000

echo -^> UI   http://127.0.0.1:5173
start "AgentAutonome-UI" /D "%~dp0web" cmd /k npm run dev -- --host 127.0.0.1 --port 5173

echo.
echo Deux fenetres ouvertes ^(API + UI^). Ferme-les pour arreter.
echo Ouvre http://127.0.0.1:5173
endlocal
