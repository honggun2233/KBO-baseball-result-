# KBO Bot - Windows 작업 스케줄러 등록 (PowerShell)
# 실행 방법: PowerShell을 관리자 권한으로 열고 아래 명령 실행
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   & "C:\project\야구 결과 송신 Project\install_service.ps1"

$TaskName  = "KBO_Baseball_Bot"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$MainPy    = Join-Path $ScriptDir "main.py"

# Python 경로 자동 탐색 (pythonw 우선 — 콘솔 창 없이 실행)
$PythonWCmd = Get-Command pythonw -ErrorAction SilentlyContinue
if ($PythonWCmd) {
    $PythonW = $PythonWCmd.Source
} else {
    $PythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($PythonCmd) {
        $PythonW = $PythonCmd.Source
    } else {
        Write-Host "ERROR: Python을 찾을 수 없습니다." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  KBO Bot 작업 스케줄러 등록" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Python : $PythonW"
Write-Host "스크립트: $MainPy"
Write-Host ""

# 기존 작업 삭제
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# 작업 구성
$Action  = New-ScheduledTaskAction -Execute $PythonW -Argument "`"$MainPy`"" -WorkingDirectory $ScriptDir
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -RunLevel Limited `
    -Force | Out-Null

# 등록 확인
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($Task) {
    Write-Host "등록 성공!" -ForegroundColor Green
    Write-Host "  상태: $($Task.State)"
    Write-Host "  Windows 로그인 시 자동 실행됩니다."
    Write-Host ""

    $Answer = Read-Host "지금 바로 시작할까요? (y/n)"
    if ($Answer -eq "y" -or $Answer -eq "Y") {
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 2
        $Info = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Host "시작됨! 마지막 실행: $($Info.LastRunTime)" -ForegroundColor Green
    }
} else {
    Write-Host "등록 실패. 관리자 권한으로 실행했는지 확인하세요." -ForegroundColor Red
}

Write-Host ""
Write-Host "관리 명령어:"
Write-Host "  중지 : Stop-ScheduledTask  -TaskName '$TaskName'"
Write-Host "  시작 : Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "  삭제 : Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
Write-Host ""
pause
