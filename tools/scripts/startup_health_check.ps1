$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$requiredPaths = @(
  'apps/cli/requirements.txt',
  'tools/scripts/install_hook_chain.ps1',
  'tools/scripts/next_gate.ps1',
  'docs/映月工厂_极简歌词工坊_PRD_v2.0.json',
  'docs/ai_doc_manifest.json',
  'one law.md',
  '目录框架规范.md'
)

$missing = $false
foreach ($relPath in $requiredPaths) {
  $fullPath = Join-Path $repoRoot $relPath
  if (-not (Test-Path $fullPath)) {
    Write-Host "[startup-check][BLOCK] Missing required path: $relPath"
    $missing = $true
  }
}

$requiredCommands = @('git')
foreach ($command in $requiredCommands) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
    Write-Host "[startup-check][BLOCK] Missing required command: $command"
    $missing = $true
  }
}

$python313Ok = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
  & py -3.13 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $python313Ok = $true
  }
}

if (-not $python313Ok -and (Get-Command python3.13 -ErrorAction SilentlyContinue)) {
  & python3.13 -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $python313Ok = $true
  }
}

if (-not $python313Ok -and (Get-Command python -ErrorAction SilentlyContinue)) {
  & python -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 13) else 1)" | Out-Null
  if ($LASTEXITCODE -eq 0) {
    $python313Ok = $true
  }
}

if (-not $python313Ok) {
  Write-Host "[startup-check][BLOCK] Python 3.13 runtime not available (checked py -3.13 / python3.13 / python)."
  $missing = $true
}

if ($missing) {
  exit 1
}

Write-Host "[startup-check] OK"
exit 0
