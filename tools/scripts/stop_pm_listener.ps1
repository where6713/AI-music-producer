$pidFile = ".tmp/pm_listener.pid"
if (!(Test-Path $pidFile)) {
  Write-Output "pm-listener not running"
  exit 0
}

$listenerPid = (Get-Content $pidFile -Raw).Trim()
if ($listenerPid) {
  $proc = Get-Process -Id ([int]$listenerPid) -ErrorAction SilentlyContinue
  if ($proc) {
    Stop-Process -Id ([int]$listenerPid) -Force
  }
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Write-Output "pm-listener stopped"
