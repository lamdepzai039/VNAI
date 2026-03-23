@echo off
echo [*] Dang tao moi truong ao (Virtual Environment)...
python -m venv venv_vnai
echo [*] Dang cai dat cac thu vien can thiet...
.\venv_vnai\bin\pip install --upgrade pip
.\venv_vnai\bin\pip install pyngrok requests Flask Flask-SQLAlchemy google-generativeai openai pillow python-dotenv gunicorn googlesearch-python
echo [OK] Da cai dat xong! Ban co the chay file CHAY_AI_TOAN_CAU.py
pause
