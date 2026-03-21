@echo off
title Cai dat va Khoi tao VNAI Cloud
echo ======================================================
echo 🚀 DANG TU DONG CAI DAT DICH VU CLOUD CHO AI...
echo ======================================================

:: 1. Kiem tra va cai dat Git bang winget (co san tren Windows 10/11)
echo [*] Dang kiem tra Git...
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Khong tim thay Git. Dang tu dong tai va cai dat Git cho ban...
    winget install --id Git.Git -e --source winget
    echo [OK] Da cai dat Git xong! Hay khoi dong lai Trae va chay lai file nay.
    pause
    exit
) else (
    echo [OK] Git da san sang.
)

:: 2. Khoi tao Git cho du an
echo [*] Dang khoi tao du an...
git init
git add .
git commit -m "Initial commit - San sang len Cloud"

echo ======================================================
echo ✨ HOAN THANH BUOC 1!
echo ======================================================
echo Bay gio ban hay lam 2 viec cuoi cung:
echo 1. Len github.com tao 1 Repository moi.
echo 2. Copy link Repository do va chay file 'BUOC_2_DAY_CODE_LEN_WEB.bat'.
echo ======================================================
pause