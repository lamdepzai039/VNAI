@echo off
title KICH HOAT VNAI - AI CUA BAN DANG LEN MANG...
echo ======================================================
echo 🚀 DANG KHOI DONG HE THONG VNAI...
echo ======================================================

:: 1. Kiem tra va tao moi truong ao neu chua co
if not exist "venv_vnai" (
    echo [*] Dang tao moi truong ao lan dau (co the mat 1-2 phut)...
    python -m venv venv_vnai
    .\venv_vnai\bin\pip install --upgrade pip
    .\venv_vnai\bin\pip install pyngrok requests Flask Flask-SQLAlchemy google-generativeai openai pillow python-dotenv gunicorn googlesearch-python
)

:: 2. Chay AI bang moi truong ao
echo [*] Dang kich hoat AI va ket noi Internet...
.\venv_vnai\bin\python CHAY_AI_TOAN_CAU.py

pause
