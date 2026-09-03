@echo off
setlocal

if exist ".venv\Scripts\streamlit.exe" (
  call ".venv\Scripts\streamlit.exe" run "app.py"
  exit /b %ERRORLEVEL%
)

echo Could not find .venv\Scripts\streamlit.exe
echo Activate your virtual environment and install dependencies first.
exit /b 1
