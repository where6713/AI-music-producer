param(
  [string]$Repo = "where6713/AI-music-producer",
  [int]$IntervalSeconds = 25,
  [string]$RootDir = (Resolve-Path ".").Path
)

$pidFile = ".tmp/pm_listener.pid"
New-Item -ItemType Directory -Force ".tmp" | Out-Null

if (Test-Path $pidFile) {
  $existingPid = (Get-Content $pidFile -Raw).Trim()
  if ($existingPid) {
    $proc = Get-Process -Id ([int]$existingPid) -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Output ("pm-listener already running (pid={0})" -f $existingPid)
      exit 0
    }
  }
}

$worker = Join-Path $PSScriptRoot "pm_listener_worker.ps1"
$args = @(
  "-NoProfile",
  "-ExecutionPolicy", "Bypass",
  "-File", ('"{0}"' -f $worker),
  "-Repo", ('"{0}"' -f $Repo),
  "-RootDir", ('"{0}"' -f $RootDir),
  "-IntervalSeconds", $IntervalSeconds
)

$p = Start-Process -FilePath "powershell" -ArgumentList $args -WindowStyle Hidden -PassThru
$p.Id | Set-Content -Path $pidFile -Encoding ascii

Start-Sleep -Seconds 1
Write-Output ("pm-listener started (pid={0})" -f $p.Id)
