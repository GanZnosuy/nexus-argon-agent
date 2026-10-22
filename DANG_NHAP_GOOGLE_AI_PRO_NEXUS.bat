@echo off
chcp 65001 >nul 2>&1
title NEXUS - Dang Nhap Google AI Pro va Lay Cookie

python "%~dp0nexus_menu.py"

if %ERRORLEVEL% neq 0 (
    echo.
    echo Da dung hoac co loi. Nhan phim bat ky de thoat...
    pause >nul
)
