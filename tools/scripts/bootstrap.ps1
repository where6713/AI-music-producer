param(
  [switch]$InstallDeps,
  [switch]$SkipHealthCheck
)

$ErrorActionPreference = 'Stop'

function Get-Python313Command {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.13 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
    if ($LASTEXITCODE -eq 0) {
      return @('py', '-3.13')
    }
  }

  if (Get-Command python3.13 -ErrorAction SilentlyContinue) {
    & python3.13 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
    if ($LASTEXITCODE -eq 0) {
      return @('python3.13')
    }
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    & python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
    if ($LASTEXITCODE -eq 0) {
      return @('python')
    }
  }

  return $null
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$requirementsPath = Join-Path $repoRoot 'apps/cli/requirements.txt'
$hookScript = Join-Path $repoRoot 'tools/scripts/install_hook_chain.ps1'
$startupCheckScript = Join-Path $repoRoot 'tools/scripts/startup_health_check.ps1'
$evidenceDir = Join-Path $repoRoot '.sisyphus/evidence'

if (-not (Test-Path $requirementsPath)) {
  Write-Host "[bootstrap][BLOCK] Missing requirements.txt: $requirementsPath"
  exit 1
}

if (-not (Test-Path $hookScript)) {
  Write-Host "[bootstrap][BLOCK] Missing hook installer: $hookScript"
  exit 1
}

if (-not (Test-Path $startupCheckScript)) {
  Write-Host "[bootstrap][BLOCK] Missing startup health check: $startupCheckScript"
  exit 1
}

if (-not (Test-Path $evidenceDir)) {
  New-Item -Path $evidenceDir -ItemType Directory -Force | Out-Null
  Write-Host "[bootstrap] created evidence directory: $evidenceDir"
}

$pythonCmd = Get-Python313Command
if ($null -eq $pythonCmd) {
  Write-Host "[bootstrap][BLOCK] Python 3.13 is required but not found in py/python3.13/python."
  exit 1
}

$pythonExe = $pythonCmd[0]
$pythonPrefix = @()
if ($pythonCmd.Count -gt 1) {
  $pythonPrefix = $pythonCmd[1..($pythonCmd.Count - 1)]
}

& $hookScript
if ($LASTEXITCODE -ne 0) {
  Write-Host "[bootstrap][BLOCK] Hook install failed"
  exit 1
}

if ($InstallDeps) {
  Write-Host "[bootstrap] installing dependencies from apps/cli/requirements.txt"
  & $pythonExe @pythonPrefix -m pip install -r $requirementsPath
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[bootstrap][BLOCK] Dependency install failed"
    exit 1
  }
}
else {
  Write-Host "[bootstrap] skipping dependency install (use -InstallDeps to enable)"
}

if ($SkipHealthCheck) {
  Write-Host "[bootstrap] skipping startup health check (use default behavior to run it)"
}
else {
  Write-Host "[bootstrap] running startup health check"
  & $startupCheckScript
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[bootstrap][BLOCK] Startup health check failed"
    exit 1
  }
}

Write-Host "[bootstrap] OK"
exit 0
