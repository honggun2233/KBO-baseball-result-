@echo off
chcp 65001 >nul
echo =====================================================
echo   KBO Bot - Windows 작업 스케줄러 등록
echo =====================================================
echo.

:: 관리자 권한 확인
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] 이 스크립트는 관리자 권한으로 실행해야 합니다.
    echo 이 파일을 우클릭 후 "관리자 권한으로 실행" 하세요.
    pause
    exit /b 1
)

:: Python 경로 자동 감지
for /f "tokens=*" %%i in ('where pythonw 2^>nul') do set PYTHONW=%%i
if not defined PYTHONW (
    for /f "tokens=*" %%i in ('where python 2^>nul') do set PYTHONW=%%i
)
if not defined PYTHONW (
    echo [오류] Python을 찾을 수 없습니다.
    pause
    exit /b 1
)

set SCRIPT_DIR=%~dp0
set MAIN_PY=%SCRIPT_DIR%main.py

echo Python 경로: %PYTHONW%
echo 스크립트:   %MAIN_PY%
echo.

:: 기존 작업 삭제 후 재등록
schtasks /delete /tn "KBO_Baseball_Bot" /f >nul 2>&1

:: 작업 등록: 로그온 시 시작, 숨김 실행
schtasks /create ^
  /tn "KBO_Baseball_Bot" ^
  /tr "\"%PYTHONW%\" \"%MAIN_PY%\"" ^
  /sc ONLOGON ^
  /rl HIGHEST ^
  /f >nul

if %errorlevel% equ 0 (
    echo [성공] 작업 스케줄러에 등록되었습니다.
    echo        Windows 로그인 시 자동으로 백그라운드 실행됩니다.
    echo.
    echo 지금 바로 시작하시겠습니까? [Y/N]
    set /p START_NOW=
    if /i "%START_NOW%"=="Y" (
        schtasks /run /tn "KBO_Baseball_Bot"
        echo [시작됨] Bot이 백그라운드에서 실행 중입니다.
    )
) else (
    echo [오류] 작업 스케줄러 등록 실패
)

echo.
echo 관리 명령어:
echo   중지: schtasks /end /tn "KBO_Baseball_Bot"
echo   시작: schtasks /run /tn "KBO_Baseball_Bot"
echo   삭제: schtasks /delete /tn "KBO_Baseball_Bot" /f
echo.
pause
