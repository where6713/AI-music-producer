$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$requiredPaths = @(
  'docs/映月工厂_极简歌词工坊_PRD.json',
  'docs/ai_doc_manifest.json',
  'one law.md',
  '目录框架规范.md',
  'README.md'
)

$missing = @()
foreach ($relPath in $requiredPaths) {
  $fullPath = Join-Path $repoRoot $relPath
  if (-not (Test-Path $fullPath)) {
    $missing += $relPath
  }
}

$status = if ($missing.Count -eq 0) { 'DONE' } else { 'BLOCKED' }

$result = [ordered]@{
  status = $status
  required_paths = $requiredPaths
  missing_paths = $missing
}

if ($status -eq 'DONE') {
  Write-Host '[next-gate] DONE'
} else {
  Write-Host '[next-gate][BLOCK] Missing required v2.0 governance files:'
  foreach ($item in $missing) {
    Write-Host "- $item"
  }
}

$result | ConvertTo-Json -Depth 5

if ($status -ne 'DONE') {
  exit 1
}

exit 0
