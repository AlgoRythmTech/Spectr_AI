# Start the Spectr backend under the supervisor so it self-heals.
# This launches the supervisor fully detached — you can close any terminal,
# restart Claude Code, log out, and the backend stays up.
# Machine reboot is the only thing that stops it.

$base = 'C:\Users\aasri\Associate_Research\backend'
$supervisor = Join-Path $base '_supervisor.ps1'
$supervisorPidFile = Join-Path $base 'supervisor.pid'

# Don't double-start — check if supervisor is already alive
if (Test-Path $supervisorPidFile) {
    $oldPid = (Get-Content $supervisorPidFile -ErrorAction SilentlyContinue) -as [int]
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Host "Supervisor already running (PID $oldPid). Nothing to do."
        Write-Host "To restart, first run:  .\backend_stop.ps1"
        exit 0
    }
}

Write-Host "Starting Spectr backend supervisor..."

# Launch the supervisor via `cmd /c start /b` so it runs in an orphaned process
# group — completely detached from the parent PowerShell session. This is the
# only reliable way on Windows to ensure the supervisor survives when whatever
# launched it (terminal, IDE, Claude Code) closes.
$py = 'C:\Users\aasri\AppData\Local\Programs\Python\Python312\python.exe'
$pyScript = Join-Path $base '_supervisor.py'
$launchCmd = "start `"spectr-supervisor`" /B /MIN `"$py`" `"$pyScript`""
cmd /c $launchCmd

Start-Sleep -Seconds 2

if (Test-Path $supervisorPidFile) {
    $supPid = Get-Content $supervisorPidFile
    Write-Host "Supervisor started PID=$supPid. Backend launching..."
    Write-Host ""
    Write-Host "To check status:  .\backend_status.ps1"
    Write-Host "To stop backend:  .\backend_stop.ps1"
} else {
    Write-Host "Supervisor PID file not written yet. Check again in 5 seconds with .\backend_status.ps1"
}
