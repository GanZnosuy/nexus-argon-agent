@echo off
chcp 65001 >nul
title LÀM MỚI COOKIE GEMINI WEB API
echo ========================================================
echo  ĐANG LÀM MỚI COOKIES CHO TẤT CẢ DỰ ÁN GEMINI TRÊN MÁY...
echo ========================================================
if exist "%USERPROFILE%\OneDrive\Desktop\CAIDATHETTHONG\gemini_cookie_daemon.py" (
    python "%USERPROFILE%\OneDrive\Desktop\CAIDATHETTHONG\gemini_cookie_daemon.py" --once
) else (
    python "%~dp0auto_cookie_bot.py"
)
echo.
if %ERRORLEVEL% EQU 0 (
    echo [THÀNH CÔNG] Tất cả ứng dụng Gemini đã được đồng bộ cookie mới nhất!
) else (
    echo [CẢNH BÁO] Có lỗi xảy ra trong quá trình làm mới cookie.
)
echo.
timeout /t 5
