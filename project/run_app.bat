@echo off
setlocal
cd /d "%~dp0Подбор ингредиентов"
where py >nul 2>nul
if %errorlevel%==0 (
    py app.py
) else (
    python app.py
)
