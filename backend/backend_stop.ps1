# Stop the supervisor (which prevents restart) then the backend.
$base = 'C:\Users\aasri\Associate_Research\backend'

function KillPid($name, $pidFile) {
    $path = Join-Path $base $pidFile
    if (-not (Test-Path $path)) { Write-Host "$name : no PID file"; return }
    $procId = (Get-Content $path -ErrorAction SilentlyContinue) -as [int]
    if (-not $procId) { return }
    try {
        Stop-Process -Id $procId -Force -ErrorAction Stop
        Write-Host "$name : stopped PID $procId"
    } catch {
        Write-Host "$name : couldn't stop ($_)"
    }
}

# Stop supervisor first so it doesn't relaunch the backend
KillPid 'Supervisor' 'supervisor.pid'
Start-Sleep -Milliseconds 500
KillPid 'Backend   ' 'backend.pid'

# Also clean up any stragglers
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -like '*_run_backend*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue; Write-Host "Also stopped stray backend PID $($_.ProcessId)" }

Write-Host "Done."
