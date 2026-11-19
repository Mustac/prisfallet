@echo off
REM Builds the site from the sample feeds and opens it at http://localhost:8000
cd /d "%~dp0"
python scripts\update_deals.py --fixtures tests\fixtures
start http://localhost:8000
python -m http.server 8000
