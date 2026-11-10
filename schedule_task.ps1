# PowerShell Script to register Daily Cyber News Digest in Windows Task Scheduler
Param(
    [string]$Time = "07:30",
    [switch]$Remove
)

$TaskName = "CyberThreatNewsDailyDigest"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$BatchFile = Join-Path $ScriptDir "run_daily.bat"

if ($Remove) {
    Write-Host "กำลังลบ Scheduled Task '$TaskName'..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "ลบ Scheduled Task เรียบร้อยแล้ว" -ForegroundColor Green
    exit
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " ตั้งเวลารัน Cyber Threat News Digest อัตโนมัติทุกเช้า" -ForegroundColor Cyan
Write-Host " เวลาที่ตั้ง: $Time น. ของทุกวัน" -ForegroundColor Cyan
Write-Host " สคริปต์เป้าหมาย: $BatchFile" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Action
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatchFile`"" -WorkingDirectory $ScriptDir

# Trigger
$Trigger = New-ScheduledTaskTrigger -Daily -At $Time

# Settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Register Task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Cyber Threat News Digest and Word Document Generator" -Force
    Write-Host "`n[+] สำเร็จ! ได้ลงทะเบียน Task Scheduler เรียบร้อยแล้ว" -ForegroundColor Green
    Write-Host "ระบบจะทำงานอัตโนมัติทุกวันเวลา $Time น." -ForegroundColor Green
} catch {
    Write-Host "`n[-] เกิดข้อผิดพลาดในการลงทะเบียน: $_" -ForegroundColor Red
    Write-Host "กรุณาลองเปิด PowerShell ด้วยสิทธิ์ Run as Administrator" -ForegroundColor Yellow
}
