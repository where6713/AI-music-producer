param(
  [string]$TaskId = '01',
  [switch]$CreateNextTemplate,
  [switch]$Json
)

$ErrorActionPreference = 'Stop'

function Find-Evidence {
  param(
    [string]$EvidenceDir,
    [string]$RegexPattern
  )

  if (-not (Test-Path $EvidenceDir)) { return $null }
  return Get-ChildItem -Path $EvidenceDir -File | Where-Object { $_.Name -match $RegexPattern } | Select-Object -First 1
}

function Test-EvidenceDone {
  param(
    [System.IO.FileInfo]$File,
    [string[]]$RequiredKeys = @()
  )

  if ($null -eq $File) { return $false }
  $text = Get-Content $File.FullName -Raw -Encoding UTF8
  $lines = Get-Content $File.FullName -Encoding UTF8

  function Get-FieldValue {
    param(
      [string[]]$AllLines,
      [string]$Key
    )

    $prefix = "- ${Key}:"
    foreach ($line in $AllLines) {
      $trimmed = $line.Trim()
      if ($trimmed.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        return $trimmed.Substring($prefix.Length).Trim()
      }
    }
    return $null
  }

  $hasPassState =
    ($text -match '(?im)^\s*-\s*status:\s*(done|pass|passed)\s*$') -or
    ($text -match '(?im)^\s*-\s*pass_or_fail:\s*pass\s*$')

  if (-not $hasPassState) { return $false }

  foreach ($key in $RequiredKeys) {
    $value = Get-FieldValue -AllLines $lines -Key $key
    if ($null -eq $value) { return $false }
    if ([string]::IsNullOrWhiteSpace($value)) { return $false }
    if ($value -match '^(pending|todo|tbd|n/a|none|null)$') { return $false }
  }

  return $true
}

function New-TemplateFile {
  param(
    [string]$Path,
    [string[]]$Lines
  )

  if (Test-Path $Path) { return }
  $dir = Split-Path -Parent $Path
  if (-not (Test-Path $dir)) {
    New-Item -Path $dir -ItemType Directory -Force | Out-Null
  }
  Set-Content -Path $Path -Value ($Lines -join "`r`n") -Encoding UTF8
}

function Get-DerivedChecklistTaskStatus {
  param(
    [string]$NextGate
  )

  if ($NextGate -eq 'DONE') { return 'done' }
  if ($NextGate -eq 'G0' -or $NextGate -eq 'G1') { return 'todo' }
  return 'in_progress'
}

function Set-JsonObjectProperty {
  param(
    [object]$Target,
    [string]$Name,
    [object]$Value
  )

  if ($null -eq $Target) { return }

  $existing = $Target.PSObject.Properties[$Name]
  if ($existing) {
    $Target.$Name = $Value
  }
  else {
    $Target | Add-Member -MemberType NoteProperty -Name $Name -Value $Value
  }
}

function Update-ChecklistStatus {
  param(
    [string]$ChecklistPath,
    [string]$TaskId,
    [string]$NextGate
  )

  $result = [ordered]@{
    available = $false
    changed = $false
    error = $null
    targetTask = $null
    derivedStatus = $null
  }

  if (-not (Test-Path $ChecklistPath)) {
    return [pscustomobject]$result
  }

  $result.available = $true

  try {
    $checklist = Get-Content $ChecklistPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
  }
  catch {
    $result.error = "Failed to parse checklist JSON: $($_.Exception.Message)"
    return [pscustomobject]$result
  }

  if (-not $checklist -or -not $checklist.phases) {
    $result.error = 'Invalid checklist schema: missing root phases array'
    return [pscustomobject]$result
  }

  $taskOrdinal = 0
  if (-not [int]::TryParse("$TaskId", [ref]$taskOrdinal) -or $taskOrdinal -le 0) {
    $result.error = "TaskId '$TaskId' is not a positive integer"
    return [pscustomobject]$result
  }

  $indexedTasks = @()
  foreach ($phase in @($checklist.phases)) {
    foreach ($task in @($phase.tasks)) {
      $indexedTasks += [pscustomobject]@{
        Phase = $phase
        Task = $task
      }
    }
  }

  if ($taskOrdinal -gt $indexedTasks.Count) {
    $result.error = "TaskId '$TaskId' is out of range for checklist task count $($indexedTasks.Count)"
    return [pscustomobject]$result
  }

  $target = $indexedTasks[$taskOrdinal - 1]
  $derivedTaskStatus = Get-DerivedChecklistTaskStatus -NextGate $NextGate
  $result.derivedStatus = $derivedTaskStatus
  $result.targetTask = "$($target.Task.id)"

  $currentTaskStatus = "$($target.Task.status)".Trim().ToLowerInvariant()
  if ($currentTaskStatus -ne $derivedTaskStatus) {
    Set-JsonObjectProperty -Target $target.Task -Name 'status' -Value $derivedTaskStatus
    $result.changed = $true
  }

  foreach ($phase in @($checklist.phases)) {
    $phaseTasks = @($phase.tasks)
    $phaseTotal = $phaseTasks.Count
    $phaseDone = @($phaseTasks | Where-Object { "$($_.status)".Trim().ToLowerInvariant() -eq 'done' }).Count
    $phaseInProgress = @($phaseTasks | Where-Object { "$($_.status)".Trim().ToLowerInvariant() -eq 'in_progress' }).Count

    $derivedPhaseStatus = if ($phaseTotal -gt 0 -and $phaseDone -eq $phaseTotal) {
      'done'
    }
    elseif ($phaseDone -gt 0 -or $phaseInProgress -gt 0) {
      'in_progress'
    }
    else {
      'todo'
    }

    $currentPhaseStatus = "$($phase.status)".Trim().ToLowerInvariant()
    if ($currentPhaseStatus -ne $derivedPhaseStatus) {
      Set-JsonObjectProperty -Target $phase -Name 'status' -Value $derivedPhaseStatus
      $result.changed = $true
    }
  }

  if ($result.changed) {
    $checklist | ConvertTo-Json -Depth 20 | Set-Content -Path $ChecklistPath -Encoding UTF8
  }

  return [pscustomobject]$result
}

function Update-Board {
  param(
    [string]$BoardPath,
    [string]$ChecklistPath,
    [string]$TaskTag,
    [bool]$G0,
    [bool]$G1,
    [bool]$G2,
    [bool]$G3,
    [bool]$G4,
    [bool]$G5,
    [bool]$G6,
    [bool]$G7,
    [bool]$G8,
    [bool]$CiReady,
    [string]$NextGate
  )

  if (-not (Test-Path $BoardPath)) { return }

  $completed = @($G0,$G1,$G2,$G3,$G4,$G5,$G6,$G7,$G8) | Where-Object { $_ } | Measure-Object | Select-Object -ExpandProperty Count

  $m0 = if ($G0) { 'x' } else { ' ' }
  $m1 = if ($G1) { 'x' } else { ' ' }
  $m2 = if ($G2) { 'x' } else { ' ' }
  $m3 = if ($G3) { 'x' } else { ' ' }
  $m4 = if ($G4) { 'x' } else { ' ' }
  $m5 = if ($G5) { 'x' } else { ' ' }
  $m6 = if ($G6) { 'x' } else { ' ' }
  $m7 = if ($G7) { 'x' } else { ' ' }
  $m8 = if ($G8) { 'x' } else { ' ' }
  $mh = if ($G6) { 'x' } else { ' ' }
  $mc = if ($CiReady) { 'x' } else { ' ' }

  $todoLines = @()
  $todoLines += ''
  $todoLines += '## PRD Full TODO (from JSON)'
  $todoLines += ''
  $todoLines += '- Source: docs/governance/prd-tdd-checklist.json'

  if (-not (Test-Path $ChecklistPath)) {
    $todoLines += '- [ ] Checklist file not found: docs/governance/prd-tdd-checklist.json'
    $todoLines += ''
  }
  else {
    try {
      $checklist = Get-Content $ChecklistPath -Raw -Encoding UTF8 | ConvertFrom-Json -ErrorAction Stop
      if (-not $checklist -or -not $checklist.phases) {
        $todoLines += '- [ ] Invalid checklist schema: missing root `phases` array'
        $todoLines += ''
      }
      else {
        $allTasks = @()
        foreach ($phase in @($checklist.phases)) {
          foreach ($task in @($phase.tasks)) {
            $allTasks += $task
          }
        }

        $totalTasks = $allTasks.Count
        $doneTasks = @($allTasks | Where-Object { "$($_.status)".Trim().ToLowerInvariant() -eq 'done' }).Count

        $todoLines += "- Tasks Done: $doneTasks/$totalTasks"
        $todoLines += ''

        foreach ($phase in @($checklist.phases)) {
          $phaseTasks = @($phase.tasks)
          $phaseTotal = $phaseTasks.Count
          $phaseDone = @($phaseTasks | Where-Object { "$($_.status)".Trim().ToLowerInvariant() -eq 'done' }).Count
          $phaseMark = if ($phaseTotal -gt 0 -and $phaseDone -eq $phaseTotal) { 'x' } else { ' ' }
          $todoLines += "- [$phaseMark] $($phase.id) $($phase.name) ($phaseDone/$phaseTotal)"

          foreach ($task in $phaseTasks) {
            $taskMark = if ("$($task.status)".Trim().ToLowerInvariant() -eq 'done') { 'x' } else { ' ' }
            $todoLines += "  - [$taskMark] $($task.id) $($task.title)"
          }

          $todoLines += ''
        }
      }
    }
    catch {
      $todoLines += "- [ ] Failed to parse docs/governance/prd-tdd-checklist.json: $($_.Exception.Message)"
      $todoLines += ''
    }
  }

  $content = @(
    '# Development Board (Single Source)',
    '',
    '> Single source board.',
    '> Auto-updated by `tools/scripts/next_gate.ps1`.',
    '',
    '## Current State (auto)',
    '',
    "- Task: $TaskTag",
    "- Completed Gates: $completed/9",
    "- Next Gate: $NextGate",
    '',
    '## Gate Checklist (auto-enforced)',
    '',
    "- [$m0] G0 Handoff",
    "- [$m1] G1 Plan + PRD mapping",
    "- [$m2] G2 Red evidence",
    "- [$m3] G3 Green evidence",
    "- [$m4] G4 Refactor verify",
    "- [$m5] G5 Docs consistency",
    "- [$m6] G6 Hooks gate (commit-msg / pre-push)",
    "- [$m7] G7 CI + audit gate",
    "- [$m8] G8 Stage quality review",
    '',
    '## Hook / CI Link (auto)',
    '',
    "- [$mh] commit-msg passed",
    "- [$mh] pre-push passed",
    "- [$mc] CI workflow configured",
    ''
  )

  $content += $todoLines
  $content += @(
    '## Command',
    '',
    '```powershell',
    'powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/next_gate.ps1" -TaskId "01"',
    '```'
  )

  Set-Content -Path $BoardPath -Value ($content -join "`r`n") -Encoding UTF8
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$handoffPath = Join-Path $repoRoot 'docs/templates/handoff.md'
$evidenceDir = Join-Path $repoRoot '.sisyphus/evidence'
$workflowDir = Join-Path $repoRoot '.github/workflows'
$boardPath = Join-Path $repoRoot 'docs/governance/dev-board.md'
$checklistPath = Join-Path $repoRoot 'docs/governance/prd-tdd-checklist.json'

$taskTag = "task-$TaskId"

$handoffContent = if (Test-Path $handoffPath) { Get-Content $handoffPath -Raw -Encoding UTF8 } else { '' }

$g0 = (Test-Path $handoffPath) -and ($handoffContent.Length -gt 600)

$g1File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-plan-"
$g2File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-exec-red-"
$g3File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-exec-green-"
$g4File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-verify-gate-g4"
$g5File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-verify-gate-g5"
$g6File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-verify-gate-g6"

$g1 = $g1File -ne $null
$g2 = Test-EvidenceDone -File $g2File -RequiredKeys @('command logs', 'test logs', 'decision')
$g3 = Test-EvidenceDone -File $g3File -RequiredKeys @('command logs', 'test logs', 'decision')
$g4 = Test-EvidenceDone -File $g4File -RequiredKeys @('command logs', 'decision')
$g5 = Test-EvidenceDone -File $g5File -RequiredKeys @('command logs', 'decision')
$g6 = Test-EvidenceDone -File $g6File -RequiredKeys @('command logs', 'decision')

$hasWorkflow = (Test-Path $workflowDir) -and ((Get-ChildItem -Path $workflowDir -File -Filter *.yml -ErrorAction SilentlyContinue).Count -gt 0 -or (Get-ChildItem -Path $workflowDir -File -Filter *.yaml -ErrorAction SilentlyContinue).Count -gt 0)
$g7File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-verify-gate-g7"
$g7Evidence = Test-EvidenceDone -File $g7File -RequiredKeys @('command logs', 'decision')
$g7 = $g7Evidence -and $hasWorkflow

$g8File = Find-Evidence -EvidenceDir $evidenceDir -RegexPattern "^$taskTag-verify-gate-g8"
$g8 = Test-EvidenceDone -File $g8File -RequiredKeys @('command logs', 'decision')

$nextGate = if (-not $g0) { 'G0' }
elseif (-not $g1) { 'G1' }
elseif (-not $g2) { 'G2' }
elseif (-not $g3) { 'G3' }
elseif (-not $g4) { 'G4' }
elseif (-not $g5) { 'G5' }
elseif (-not $g6) { 'G6' }
elseif (-not $g7) { 'G7' }
elseif (-not $g8) { 'G8' }
else { 'DONE' }

$nextTemplate = $null
if ($nextGate -eq 'G1') { $nextTemplate = Join-Path $evidenceDir "$taskTag-plan-prd-mapping.txt" }
elseif ($nextGate -eq 'G2') { $nextTemplate = Join-Path $evidenceDir "$taskTag-exec-red-log.txt" }
elseif ($nextGate -eq 'G3') { $nextTemplate = Join-Path $evidenceDir "$taskTag-exec-green-log.txt" }
elseif ($nextGate -eq 'G4') { $nextTemplate = Join-Path $evidenceDir "$taskTag-verify-gate-g4.txt" }
elseif ($nextGate -eq 'G5') { $nextTemplate = Join-Path $evidenceDir "$taskTag-verify-gate-g5.txt" }
elseif ($nextGate -eq 'G6') { $nextTemplate = Join-Path $evidenceDir "$taskTag-verify-gate-g6.txt" }
elseif ($nextGate -eq 'G7') { $nextTemplate = Join-Path $evidenceDir "$taskTag-verify-gate-g7.txt" }
elseif ($nextGate -eq 'G8') { $nextTemplate = Join-Path $evidenceDir "$taskTag-verify-gate-g8.txt" }

if ($CreateNextTemplate -and $nextGate -ne 'G0' -and $nextGate -ne 'DONE' -and $nextTemplate) {
  New-TemplateFile -Path $nextTemplate -Lines @(
    "# $taskTag $nextGate evidence",
    "",
    "- gate: $nextGate",
    "- task: $taskTag",
    "- status: pending",
    "",
    "## required",
    "- command logs:",
    "- test logs:",
    "- decision:",
    "",
    "## result",
    "- pass_or_fail:"
  )
}

$checklistUpdate = Update-ChecklistStatus -ChecklistPath $checklistPath -TaskId $TaskId -NextGate $nextGate
if ($checklistUpdate.error) {
  Write-Warning "[next-gate] checklist update skipped: $($checklistUpdate.error)"
}

Update-Board -BoardPath $boardPath -ChecklistPath $checklistPath -TaskTag $taskTag -G0:$g0 -G1:$g1 -G2:$g2 -G3:$g3 -G4:$g4 -G5:$g5 -G6:$g6 -G7:$g7 -G8:$g8 -CiReady:$hasWorkflow -NextGate:$nextGate

$status = [ordered]@{
  task = $taskTag
  gates = [ordered]@{
    G0 = $g0
    G1 = $g1
    G2 = $g2
    G3 = $g3
    G4 = $g4
    G5 = $g5
    G6 = $g6
    G7 = $g7
    G8 = $g8
  }
  ciWorkflowReady = $hasWorkflow
  nextGate = $nextGate
  nextTemplate = $nextTemplate
}

if ($Json) {
  $status | ConvertTo-Json -Depth 8
  exit 0
}

Write-Host "[next-gate] task=$($status.task)"
Write-Host "[next-gate] G0=$g0 G1=$g1 G2=$g2 G3=$g3 G4=$g4 G5=$g5 G6=$g6 G7=$g7 G8=$g8"
Write-Host "[next-gate] ciWorkflowReady=$hasWorkflow"
Write-Host "[next-gate] nextGate=$nextGate"
if ($nextTemplate) {
  Write-Host "[next-gate] suggestedEvidenceFile=$nextTemplate"
}

exit 0
