# Windows Task Scheduler 등록 스크립트
# 관리자 권한으로 실행 필요

$taskName = "MetaAdLibrary_DailyCollect"
$taskDescription = "Meta Ad Library 광고 수집 - 매일 오전 9시"
$scriptPath = "C:\git\vibe\260112_meta_library\run_daily.bat"
$workingDir = "C:\git\vibe\260112_meta_library"

# 기존 태스크가 있으면 삭제
$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "기존 태스크 삭제됨: $taskName"
}

# 트리거: 매일 오전 9시
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# 액션: 배치 파일 실행
$action = New-ScheduledTaskAction -Execute $scriptPath -WorkingDirectory $workingDir

# 설정: 컴퓨터가 깨어있지 않아도 실행, 놓친 실행은 즉시 시작
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

# 태스크 등록
Register-ScheduledTask -TaskName $taskName -Description $taskDescription -Trigger $trigger -Action $action -Settings $settings -RunLevel Highest

Write-Host ""
Write-Host "=========================================="
Write-Host " Task Scheduler 등록 완료!"
Write-Host "=========================================="
Write-Host " 태스크명: $taskName"
Write-Host " 실행 시간: 매일 오전 9:00"
Write-Host " 스크립트: $scriptPath"
Write-Host ""
Write-Host "확인 명령: Get-ScheduledTask -TaskName '$taskName'"
Write-Host "수동 실행: Start-ScheduledTask -TaskName '$taskName'"
Write-Host ""
