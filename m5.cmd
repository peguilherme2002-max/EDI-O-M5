@echo off
setlocal
set "PYTHONPATH=%~dp0motor"
python -m m5 %*
