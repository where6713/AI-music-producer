$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$manifestPath = Join-Path $root 'docs/ai_doc_manifest.json'

if (!(Test-Path $manifestPath)) {
  Write-Host "[docs-check][BLOCK] Missing manifest: $manifestPath"
  exit 1
}

$manifest = Get-Content $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json

$mdFiles = Get-ChildItem -Path $root -Filter *.md -File
$fail = $false

foreach ($topic in $manifest.canonical_topics) {
  $ownerPath = Join-Path $root $topic.owner_file
  if (!(Test-Path $ownerPath)) {
    Write-Host "[docs-check][BLOCK] Missing owner file: $($topic.owner_file)"
    $fail = $true
    continue
  }

  $ownerText = Get-Content $ownerPath -Raw -Encoding UTF8
  if ($ownerText -notmatch [regex]::Escape($topic.owner_marker)) {
    Write-Host "[docs-check][BLOCK] Owner marker missing in $($topic.owner_file): $($topic.owner_marker)"
    $fail = $true
  }

  foreach ($needle in $topic.forbidden_fulltext_outside_owner) {
    foreach ($file in $mdFiles) {
      if ($file.Name -eq $topic.owner_file) { continue }
      $text = Get-Content $file.FullName -Raw -Encoding UTF8
      if ($text -match [regex]::Escape($needle)) {
        # 允许“引用式”出现：同一行包含 owner 文件名或“见/参考/reference”关键词
        $lines = Get-Content $file.FullName -Encoding UTF8
        $hitIndex = 0
        foreach ($line in $lines) {
          $hitIndex++
          if ($line -match [regex]::Escape($needle)) {
            $isReference = ($line -match [regex]::Escape($topic.owner_file)) -or ($line -match '见|参考|reference|引用')
            if (-not $isReference) {
              Write-Host "[docs-check][BLOCK] Duplicate normative text outside owner: $($topic.topic_id)"
              Write-Host "  file: $($file.FullName):$hitIndex"
              Write-Host "  text: $needle"
              $fail = $true
            }
          }
        }
      }
    }
  }
}

if ($fail) {
  exit 1
}

Write-Host "[docs-check] OK"
exit 0
