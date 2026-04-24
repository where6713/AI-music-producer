$pidFile = ".tmp/pm_audit.pid"
if (!(Test-Path $pidFile)) {
  Write-Output "pm-audit worker not running (no pid file)"
  exit 1
}

$auditPid = (Get-Content $pidFile -Raw).Trim()
if (-not $auditPid) {
  Write-Output "pm-audit worker not running (empty pid file)"
  exit 1
}

$proc = Get-Process -Id ([int]$auditPid) -ErrorAction SilentlyContinue
if (-not $proc) {
  Write-Output ("pm-audit worker not running (stale pid={0})" -f $auditPid)
  exit 1
}

Write-Output ("pm-audit worker running (pid={0})" -f $auditPid)

if (Test-Path ".tmp/pm_audit.log") {
  Write-Output "--- recent log ---"
  Get-Content ".tmp/pm_audit.log" -Tail 20
}
