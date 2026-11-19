@echo off
REM Fetches the real feeds using the keys in .env, then opens the site at http://localhost:8000
cd /d "%~dp0"
if exist .env (for /f "usebackq eol=# tokens=1,* delims==" %%a in (".env") do set "%%a=%%b")
python scripts\update_deals.py
start http://localhost:8000
python -m http.server 8000
