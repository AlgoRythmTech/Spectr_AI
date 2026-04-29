# Backend supervisor — keeps uvicorn alive.
# If the backend process exits for any reason (crash, OOM, unhandled exception,
# parent-shell GC), this supervisor restarts it within seconds.
#
# Launch this file detached:
#   Start-Process powershell -ArgumentList '-WindowStyle','Hidden',
#     '-ExecutionPolicy','Bypass','-File','C:\Users\aasri\Associate_Research\backend\_supervisor.ps1'
#
# Stop the supervisor (and backend) cleanly:
#   Stop-Process -Id (Get-Content C:\Users\aasri\Associate_Research\backend\supervisor.pid) -Force
#   Stop-Process -Id (Get-Content C:\Users\aasri\Associate_Research\backend\backend.pid) -Force

$ErrorActionPreference = 'Continue'
$base = 'C:\Users\aasri\Associate_Research\backend'
$py = 'C:\Users\aasri\AppData\Local\Programs\Python\Python312\python.exe'
$script = Join-Path $base '_run_backend.py'
$supervisorPidFile = Join-Path $base 'supervisor.pid'
$supervisorLog = Join-Path $base 'supervisor.log'

# Record our own PID so the user can kill the supervisor cleanly
$PID | Out-File -FilePath $supervisorPidFile -Encoding ascii

function Log($msg) {
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    "$ts  $msg" | Out-File -FilePath $supervisorLog -Append -Encoding utf8
}

Log "Supervisor starting. supervisor PID=$PID. Launching backend loop."

$consecutiveFastFailures = 0
while ($true) {
    $start = Get-Date

    # Clean stop of any dangling backend before relaunch
    if (Test-Path (Join-Path $base 'backend.pid')) {
        $oldPid = Get-Content (Join-Path $base 'backend.pid') -ErrorAction SilentlyContinue
        if ($oldPid) {
            try { Stop-Process -Id $oldPid -Force -ErrorAction SilentlyContinue } catch {}
        }
    }

    Log "Launching backend..."
    $stdout = Join-Path $base 'backend_stdout.log'
    $stderr = Join-Path $base 'backend_stderr.log'
    $proc = Start-Process -FilePath $py -ArgumentList $script `
        -WorkingDirectory $base -WindowStyle Hidden `
        -RedirectStandardOutput $stdout -RedirectStandardError $stderr `
        -PassThru

    Log "Backend launched PID=$($proc.Id). Waiting for process exit..."
    $proc.WaitForExit()
    $exitCode = $proc.ExitCode
    $uptime = (Get-Date) - $start
    Log "Backend exited code=$exitCode uptime=$([int]$uptime.TotalSeconds)s"

    # Crash-loop protection — if backend dies in <15s repeatedly, back off
    if ($uptime.TotalSeconds -lt 15) {
        $consecutiveFastFailures++
    } else {
        $consecutiveFastFailures = 0
    }

    if ($consecutiveFastFailures -ge 5) {
        Log "FIVE consecutive fast failures — backing off 60s before retry."
        Start-Sleep -Seconds 60
        $consecutiveFastFailures = 0
    } else {
        Start-Sleep -Seconds 3
    }
}
