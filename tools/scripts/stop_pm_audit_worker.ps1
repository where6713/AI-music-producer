$pidFile = ".tmp/pm_audit.pid"
if (!(Test-Path $pidFile)) {
  Write-Output "pm-audit worker not running"
  exit 0
}

$auditPid = (Get-Content $pidFile -Raw).Trim()
if ($auditPid) {
  $proc = Get-Process -Id ([int]$auditPid) -ErrorAction SilentlyContinue
  if ($proc) {
    Stop-Process -Id ([int]$auditPid) -Force
  }
}

Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
Write-Output "pm-audit worker stopped"
