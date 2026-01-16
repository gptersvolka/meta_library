@echo off
REM Meta Ad Library 일일 수집 배치 파일
cd /d "C:\git\vibe\260112_meta_library"
call venv\Scripts\activate.bat
python -m src.08_scheduler run_now
