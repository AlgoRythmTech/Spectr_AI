# Quick status check — shows backend + supervisor state.
$base = 'C:\Users\aasri\Associate_Research\backend'

function CheckPid($name, $pidFile) {
    $path = Join-Path $base $pidFile
    if (-not (Test-Path $path)) { Write-Host "$name : no PID file"; return }
    $procId = (Get-Content $path -ErrorAction SilentlyContinue) -as [int]
    if (-not $procId) { Write-Host "$name : PID file empty"; return }
    $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($p) {
        $mem = [math]::Round($p.WorkingSet64 / 1MB, 0)
        Write-Host "$name : alive (PID=$procId, ${mem}MB)"
    } else {
        Write-Host "$name : DEAD (PID file says $procId, process gone)"
    }
}

Write-Host "=== Spectr backend status ==="
CheckPid 'Supervisor' 'supervisor.pid'
CheckPid 'Backend   ' 'backend.pid'

Write-Host ""
Write-Host "--- HTTP health ---"
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5 -UseBasicParsing
    Write-Host "HTTP $($r.StatusCode): $($r.Content)"
} catch {
    Write-Host "HTTP check FAILED: $_"
}

Write-Host ""
Write-Host "--- Supervisor log (last 15 lines) ---"
$log = Join-Path $base 'supervisor.log'
if (Test-Path $log) { Get-Content $log -Tail 15 } else { Write-Host "(no log yet)" }
