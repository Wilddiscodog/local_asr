@echo off
setlocal
cd /d "%~dp0"
set PY=
where py >nul 2>&1 && set PY=py -3.11
if not defined PY if exist "%LocalAppData%\Programs\Python\Python311\python.exe" set PY="%LocalAppData%\Programs\Python\Python311\python.exe"
if not defined PY set PY=python
echo Using: %PY%
%PY% -c "import sherpa_onnx" 2>nul || (
  echo Installing requirements...
  %PY% -m pip install -r requirements.txt
)
if not exist "models\sherpa-onnx-paraformer-zh-2023-09-14\tokens.txt" (
  echo Downloading model...
  %PY% download_model.py
)
echo Starting server on 0.0.0.0:8765 ...
%PY% server.py --host 0.0.0.0 --port 8765
endlocal
