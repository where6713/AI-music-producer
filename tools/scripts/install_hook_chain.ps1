$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$hooksRelativePath = 'tools/githooks'
$hooksPath = Join-Path $repoRoot $hooksRelativePath

if (-not (Test-Path $hooksPath)) {
  Write-Host "[hook-install][BLOCK] hooks directory missing: $hooksPath"
  exit 1
}

$requiredHooks = @('pre-commit', 'commit-msg', 'pre-push', 'post-commit')
foreach ($hook in $requiredHooks) {
  $hookFile = Join-Path $hooksPath $hook
  if (-not (Test-Path $hookFile)) {
    Write-Host "[hook-install][BLOCK] required hook missing: $hookFile"
    exit 1
  }
}

git config core.hooksPath $hooksRelativePath
$actualHooksPath = git config --get core.hooksPath

if ($actualHooksPath -ne $hooksRelativePath) {
  Write-Host "[hook-install][BLOCK] core.hooksPath mismatch. expected=$hooksRelativePath actual=$actualHooksPath"
  exit 1
}

Write-Host "[hook-install] core.hooksPath=$actualHooksPath"
Write-Host "[hook-install] hook chain installed"
exit 0
