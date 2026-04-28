$pidFile = ".tmp/pm_listener.pid"
if (!(Test-Path $pidFile)) {
  Write-Output "pm-listener not running (no pid file)"
  exit 1
}

$listenerPid = (Get-Content $pidFile -Raw).Trim()
if (-not $listenerPid) {
  Write-Output "pm-listener not running (empty pid file)"
  exit 1
}

$proc = Get-Process -Id ([int]$listenerPid) -ErrorAction SilentlyContinue
if (-not $proc) {
  Write-Output ("pm-listener not running (stale pid={0})" -f $listenerPid)
  exit 1
}

Write-Output ("pm-listener running (pid={0})" -f $listenerPid)

if (Test-Path ".tmp/pm_listener.log") {
  Write-Output "--- recent log ---"
  Get-Content ".tmp/pm_listener.log" -Tail 20
}
