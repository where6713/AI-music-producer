param(
  [string]$Repo = "where6713/AI-music-producer",
  [int]$IntervalSeconds = 25,
  [string]$RootDir = ".",
  [string]$StatePath = ".tmp/pm_listener_state.json",
  [string]$LogPath = ".tmp/pm_listener.log"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

New-Item -ItemType Directory -Force ".tmp" | Out-Null
Set-Location $RootDir

$resolvedStatePath = if ([System.IO.Path]::IsPathRooted($StatePath)) { $StatePath } else { Join-Path $RootDir $StatePath }
$resolvedLogPath = if ([System.IO.Path]::IsPathRooted($LogPath)) { $LogPath } else { Join-Path $RootDir $LogPath }
New-Item -ItemType Directory -Force (Split-Path -Parent $resolvedStatePath) | Out-Null

function Write-Log([string]$Message) {
  $line = "{0} {1}" -f (Get-Date -Format o), $Message
  Add-Content -Path $resolvedLogPath -Value $line
}

function Get-OpenPrMap([string]$RepoName) {
  $map = @{}
  $tempJson = Join-Path $RootDir ".tmp/pm_listener_prs.json"
  gh pr list --repo $RepoName --state open --limit 50 --json number,headRefOid | Set-Content -Path $tempJson -Encoding utf8
  $arr = Get-Content -Path $tempJson -Raw | ConvertFrom-Json
  foreach ($pr in $arr) {
    $map[[string]$pr.number] = [string]$pr.headRefOid
  }
  return $map
}

if (!(Test-Path $resolvedStatePath)) {
  $seed = Get-OpenPrMap -RepoName $Repo
  ($seed | ConvertTo-Json -Compress) | Set-Content -Path $resolvedStatePath -Encoding utf8
  Write-Log ("seeded {0} open PRs" -f $seed.Keys.Count)
}

Write-Log "pm-listener worker started"

while ($true) {
  try {
    $old = @{}
    if (Test-Path $resolvedStatePath) {
      $txt = Get-Content -Path $resolvedStatePath -Raw
      if ($txt) {
        $obj = $txt | ConvertFrom-Json
        foreach ($p in $obj.PSObject.Properties) {
          $old[$p.Name] = [string]$p.Value
        }
      }
    }

    $now = Get-OpenPrMap -RepoName $Repo
    foreach ($k in $now.Keys) {
      if (-not $old.ContainsKey($k)) {
        gh pr comment $k --repo $Repo --body "[PM-LISTENER] PR detected. Entering PM audit queue. Please wait for GO/NO-GO review." | Out-Null
        Write-Log ("new PR detected #{0}" -f $k)
      }
      elseif ($old[$k] -ne $now[$k]) {
        gh pr comment $k --repo $Repo --body "[PM-LISTENER] New commit detected. PM will re-run audit and reply with GO/NO-GO." | Out-Null
        Write-Log ("new commit detected on PR #{0}" -f $k)
      }
    }

    ($now | ConvertTo-Json -Compress) | Set-Content -Path $resolvedStatePath -Encoding utf8
    Write-Log "heartbeat"
  }
  catch {
    Write-Log ("error: {0}" -f $_.Exception.Message)
  }

  Start-Sleep -Seconds $IntervalSeconds
}
