param(
  [string]$Repo = "where6713/AI-music-producer",
  [int]$IntervalSeconds = 45,
  [string]$RootDir = ".",
  [string]$StatePath = ".tmp/pm_audit_state.json",
  [string]$LogPath = ".tmp/pm_audit.log"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $global:PSNativeCommandUseErrorActionPreference = $false
}

Set-Location $RootDir

$resolvedStatePath = if ([System.IO.Path]::IsPathRooted($StatePath)) { $StatePath } else { Join-Path $RootDir $StatePath }
$resolvedLogPath = if ([System.IO.Path]::IsPathRooted($LogPath)) { $LogPath } else { Join-Path $RootDir $LogPath }
$wtRoot = Join-Path $RootDir ".tmp/pm_audit_worktrees"

New-Item -ItemType Directory -Force (Split-Path -Parent $resolvedStatePath) | Out-Null
New-Item -ItemType Directory -Force $wtRoot | Out-Null

function Write-Log([string]$Message) {
  $line = "{0} {1}" -f (Get-Date -Format o), $Message
  Add-Content -Path $resolvedLogPath -Value $line
}

function Get-OpenPrMap([string]$RepoName) {
  $map = @{}
  $rows = gh pr list --repo $RepoName --state open --limit 50 --json number,headRefOid --jq '.[] | [.number, .headRefOid] | @tsv'
  foreach ($line in $rows) {
    if (-not $line) { continue }
    $parts = $line -split "`t", 2
    if ($parts.Count -eq 2) {
      $map[[string]$parts[0]] = [string]$parts[1]
    }
  }
  return $map
}

function Get-StateMap {
  $state = @{}
  if (Test-Path $resolvedStatePath) {
    $txt = Get-Content -Path $resolvedStatePath -Raw
    if ($txt) {
      $obj = $txt | ConvertFrom-Json
      foreach ($p in $obj.PSObject.Properties) {
        $state[$p.Name] = [string]$p.Value
      }
    }
  }
  return $state
}

function Save-StateMap([hashtable]$State) {
  ($State | ConvertTo-Json -Compress) | Set-Content -Path $resolvedStatePath -Encoding utf8
}

function Ensure-Worktree([string]$CommitSha, [string]$PrNumber) {
  $wtPath = Join-Path $wtRoot ("pr-{0}" -f $PrNumber)
  if (Test-Path $wtPath) {
    git -C $RootDir worktree remove --force "$wtPath" | Out-Null
  }
  git -C $RootDir worktree add --force "$wtPath" $CommitSha | Out-Null
  return $wtPath
}

function Run-Check([string]$WorktreePath, [string]$Command) {
  Push-Location $WorktreePath
  try {
    $tmpDir = Join-Path $WorktreePath ".tmp"
    New-Item -ItemType Directory -Force $tmpDir | Out-Null
    $stdoutFile = Join-Path $tmpDir "pm_audit_stdout.txt"
    $stderrFile = Join-Path $tmpDir "pm_audit_stderr.txt"

    $proc = Start-Process -FilePath "powershell" -ArgumentList @("-NoProfile", "-Command", $Command) -RedirectStandardOutput $stdoutFile -RedirectStandardError $stderrFile -PassThru -Wait
    $exitCode = [int]$proc.ExitCode
    $stdout = if (Test-Path $stdoutFile) { Get-Content -Path $stdoutFile -Raw } else { "" }
    $stderr = if (Test-Path $stderrFile) { Get-Content -Path $stderrFile -Raw } else { "" }
    $output = ($stdout + "`n" + $stderr).Trim()

    return @{
      command = $Command
      output = $output
      exit_code = $exitCode
      pass = ($exitCode -eq 0)
    }
  }
  finally {
    Pop-Location
  }
}

function Compact-Line([string]$Text) {
  if (-not $Text) { return "" }
  $line = ($Text -split "`r?`n" | Where-Object { $_.Trim() -ne "" } | Select-Object -Last 1)
  if (-not $line) { return "" }
  return $line.Trim()
}

function Audit-Pr([string]$PrNumber, [string]$CommitSha) {
  Write-Log ("audit start pr=#{0} sha={1}" -f $PrNumber, $CommitSha)
  $wt = Ensure-Worktree -CommitSha $CommitSha -PrNumber $PrNumber

  $pytest = Run-Check -WorktreePath $wt -Command "python -m pytest -q"
  $gates = Run-Check -WorktreePath $wt -Command "python -m apps.cli.main gate-check --all"

  $verdict = if ($pytest.pass -and $gates.pass) { "GO" } else { "NO-GO" }
  $body = @(
    "[PM-AUTO-AUDIT] PR #$PrNumber @ $CommitSha",
    "- pytest -q: $([string]::Format('{0}', $(if ($pytest.pass) {'PASS'} else {'FAIL'})))",
    "- gate-check --all: $([string]::Format('{0}', $(if ($gates.pass) {'PASS'} else {'FAIL'})))",
    "- verdict: $verdict",
    "",
    "quick-output:",
    "- pytest: $(Compact-Line -Text $pytest.output)",
    "- gates: $(Compact-Line -Text $gates.output)",
    "",
    "note: This is automated pre-audit. Final GO/NO-GO still follows PM Role & Rule and human review."
  ) -join "`n"

  gh pr comment $PrNumber --repo $Repo --body $body | Out-Null
  Write-Log ("audit done pr=#{0} verdict={1}" -f $PrNumber, $verdict)

  return @{ verdict = $verdict }
}

if (!(Test-Path $resolvedStatePath)) {
  $seed = @{}
  Save-StateMap -State $seed
  Write-Log "seeded empty audit state"
}

Write-Log "pm-audit worker started"

while ($true) {
  try {
    $state = Get-StateMap
    $open = Get-OpenPrMap -RepoName $Repo
    foreach ($pr in $open.Keys) {
      $sha = $open[$pr]
      $seen = if ($state.ContainsKey($pr)) { $state[$pr] } else { "" }
      if ($sha -and $sha -ne $seen) {
        Audit-Pr -PrNumber $pr -CommitSha $sha | Out-Null
        $state[$pr] = $sha
      }
    }
    Save-StateMap -State $state
    Write-Log "heartbeat"
  }
  catch {
    Write-Log ("error: {0}" -f $_.Exception.Message)
  }

  Start-Sleep -Seconds $IntervalSeconds
}
