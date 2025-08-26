@echo off
setlocal
for /f "delims=" %%A in (.env) do set %%A
python app/main.py
