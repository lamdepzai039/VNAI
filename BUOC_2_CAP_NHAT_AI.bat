@echo off
title Day code len Cloud va Cap nhat AI
echo ======================================================
echo 🚀 DANG TU DONG CAP NHAT AI CUA BAN LEN WEB...
echo ======================================================

:: 1. Hoi link GitHub neu chua co
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    set repo_url=https://github.com/lamdepzai039/VNAI.git
    git remote add origin https://github.com/lamdepzai039/VNAI.git
)

:: 2. Day code len
echo [*] Dang day du lieu len GitHub...
git branch -M main
git add .
git commit -m "Auto-update: %date% %time%"
git push -u origin main

echo ======================================================
echo ✨ DA CAP NHAT XONG!
echo ======================================================
echo Neu ban da ket noi Render voi GitHub, AI se tu dong
echo cap nhat tinh nang moi trong vong 1 phut!
echo ======================================================
pause