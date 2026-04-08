#!/usr/bin/env sh
# Auto-push after successful commit hooks (opt-in)

set -eu

# Toggle via git config: oost.autoPush=true|false
auto_push_enabled="$(git config --get oost.autoPush || echo false)"
if [ "$auto_push_enabled" != "true" ]; then
  echo "[post-commit] oost.autoPush=false -> skip auto push"
  exit 0
fi

branch="$(git branch --show-current)"
if [ -z "$branch" ]; then
  echo "[post-commit] detached HEAD -> skip auto push"
  exit 0
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo "[post-commit] origin not configured -> skip auto push"
  exit 0
fi

upstream="$(git rev-parse --abbrev-ref @{upstream} 2>/dev/null || true)"
if [ -z "$upstream" ]; then
  echo "[post-commit] no upstream -> git push -u origin $branch"
  git push -u origin "$branch"
else
  echo "[post-commit] git push origin $branch"
  git push origin "$branch"
fi

echo "[post-commit] auto push done"
