@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set PY=
where py >nul 2>&1 && set "PY=py -3.11"
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
  set "PY=%LocalAppData%\Programs\Python\Python311\python.exe"
)
if not defined PY set PY=python

echo [1/4] Python: %PY%
%PY% -c "import sys; print(sys.version); assert sys.version_info >= (3, 9)" || (
  echo Need Python 3.9+
  exit /b 1
)

echo [2/4] Install build deps...
%PY% -m pip install -r requirements.txt pyinstaller || exit /b 1

echo [3/4] PyInstaller onedir...
if exist build rmdir /s /q build
if exist dist\pc_stt_server rmdir /s /q dist\pc_stt_server
%PY% -m PyInstaller --noconfirm --clean pc_stt_server.spec || exit /b 1

echo [4/4] Copy helper scripts into dist...
copy /y README.md dist\pc_stt_server\README.md >nul
(
  echo pc_stt_server - offline Chinese STT HTTP service
  echo.
  echo 1. Double-click pc_stt_server.exe  ^(first run may download ~200MB model^)
  echo 2. Or copy an existing models\ folder next to the exe to skip download
  echo 3. Open firewall for TCP 8765 if other devices need access
  echo 4. Health:  http://127.0.0.1:8765/health
  echo 5. API:     POST http://^<PC-IP^>:8765/transcribe
  echo.
  echo Args: pc_stt_server.exe --host 0.0.0.0 --port 8765 --threads 2
) > dist\pc_stt_server\使用说明.txt

echo.
echo OK: dist\pc_stt_server\
echo Zip that folder and copy to other Windows PCs ^(x64^).
echo Model is NOT inside the zip by default; first launch auto-downloads,
echo or copy tools\pc_stt\models into dist\pc_stt_server\models beforehand.
endlocal
