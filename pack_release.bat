@echo off
setlocal
cd /d "%~dp0"
if not exist "dist\pc_stt_server\pc_stt_server.exe" (
  echo Run build_exe.bat first.
  exit /b 1
)
set ZIP=dist\pc_stt_server_win64.zip
if exist "%ZIP%" del /f /q "%ZIP%"
powershell -NoProfile -Command "Compress-Archive -Path 'dist\pc_stt_server' -DestinationPath '%ZIP%' -Force"
echo Packed: %CD%\%ZIP%
echo Deploy: unzip on target PC, run pc_stt_server.exe
endlocal
