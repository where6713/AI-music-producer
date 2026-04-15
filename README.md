# AI-music-producer

Windows 11 原生 CLI 的 AI 制片人系统（开发中）。

## 当前仓库状态
- 已创建 GitHub 远程仓库并绑定 `origin`
- 已启用本地 hooks 路径：`tools/githooks`
- 已建立治理文档与 Gate 体系（G0-G8）

## 关键文档
- `AI-music-producer PRD_v1.1.md`
- `one law.md`
- `开发清单.md`
- `目录框架规范.md`

## 治理文档
- `docs/governance/gates.md`
- `docs/governance/ci-sync-checklist.md`
- `docs/governance/evidence-spec.md`
- `docs/governance/audit-schedule.md`
- `docs/governance/dev-board.md`（唯一看板）

## 开发约束（摘要）
1. 先法则，后 Hook
2. 先测试，后实现
3. 先通过 Hook，再允许流程扩张

## 快速启动（可复现）
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/bootstrap.ps1" -InstallDeps
```

说明：该命令会安装 Hook、按需安装依赖，并默认执行启动健康检查。

仅执行健康检查：
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/startup_health_check.ps1"
```
