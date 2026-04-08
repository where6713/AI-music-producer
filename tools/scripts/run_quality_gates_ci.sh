#!/usr/bin/env sh
# CI quality gates (mirror local hooks intent)

set -eu

echo "[ci-gates] start"

# 0) docs consistency
if command -v pwsh >/dev/null 2>&1; then
  pwsh -NoProfile -File "tools/scripts/check_docs_consistency.ps1"
elif command -v powershell >/dev/null 2>&1; then
  powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/check_docs_consistency.ps1"
else
  echo "[ci-gates][WARN] PowerShell not found; skip docs consistency check."
fi

# 1) block tracked audio binaries
if git ls-files | grep -Eiq '\.(wav|mp3|flac|ogg|aac|m4a)$'; then
  echo "[ci-gates][BLOCK] tracked audio binaries detected (PRD hygiene rule)."
  git ls-files | grep -Ei '\.(wav|mp3|flac|ogg|aac|m4a)$' || true
  exit 1
fi

# 2) block fuzzy script naming (RULE-13)
if git ls-files | grep -Eiq '(^|/)(temp|new|utils|helper)\.(ps1|sh|py|js|ts)$'; then
  echo "[ci-gates][BLOCK] fuzzy script naming detected (temp/new/utils/helper)."
  git ls-files | grep -Ei '(^|/)(temp|new|utils|helper)\.(ps1|sh|py|js|ts)$' || true
  exit 1
fi

# 3) root clutter guard (RULE-15)
root_files="$(git ls-files | grep -E '^[^/]+$' || true)"
if [ -n "$root_files" ]; then
  disallowed_root="$(printf '%s\n' "$root_files" | grep -Ev '^(AI-music-producer PRD_v1\.1\.md|one law\.md|开发清单\.md|目录框架规范\.md|README\.md|LICENSE|CHANGELOG\.md|\.gitignore)$' || true)"
  if [ -n "$disallowed_root" ]; then
    echo "[ci-gates][BLOCK] non-whitelisted root files detected:"
    printf '%s\n' "$disallowed_root"
    exit 1
  fi
fi

# 4) light secret scan
if git grep -nE '(AKIA[0-9A-Z]{16}|BEGIN[[:space:]]+PRIVATE[[:space:]]+KEY|api[_-]?key[[:space:]]*[:=][[:space:]]*["'"'"'"'"'"'][^"'"'"'"'"'"']+["'"'"'"'"'"'])' -- . >/dev/null 2>&1; then
  echo "[ci-gates][BLOCK] potential secrets detected in tracked files."
  git grep -nE '(AKIA[0-9A-Z]{16}|BEGIN[[:space:]]+PRIVATE[[:space:]]+KEY|api[_-]?key[[:space:]]*[:=][[:space:]]*["'"'"'"'"'"'][^"'"'"'"'"'"']+["'"'"'"'"'"'])' -- . || true
  exit 1
fi

# 5) quick tests (mirror pre-push intent)
ran_any_test=0

if command -v python >/dev/null 2>&1; then
  if [ -d "tests" ] && find tests -type f | grep -qv '\.gitkeep$'; then
    echo "[ci-gates] python -m pytest -q"
    python -m pytest -q
    ran_any_test=1
  fi
fi

if [ -f "package.json" ] && command -v npm >/dev/null 2>&1; then
  echo "[ci-gates] npm test -- --watch=false"
  npm test -- --watch=false
  ran_any_test=1
fi

if [ "$ran_any_test" -eq 0 ]; then
  echo "[ci-gates] no runnable quick tests detected; skip."
fi

echo "[ci-gates] OK"
