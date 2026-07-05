@echo off
title Resume Review Agent — Backend Server
echo.
echo  ===========================================
echo     Resume Review Agent -- Starting...
echo  ===========================================
echo.
echo  Backend:   http://localhost:8000
echo  API Docs:  http://localhost:8000/docs
echo  Health:    http://localhost:8000/health
echo.
cd /d "%~dp0backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
