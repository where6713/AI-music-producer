# CI 与本地 Hooks 同源清单

> 原则：本地过 = CI 过；本地不过 = CI 不过。

## A. 同源范围（必须全覆盖）
- `tools/githooks/pre-commit`
- `tools/githooks/commit-msg`
- `tools/githooks/pre-push`

## B. Hook ↔ CI 镜像对照

| 本地 Hook | 本地来源（SoT） | 本地检查摘要 | CI 镜像检查（对应项） | 同源验证方法 |
|---|---|---|---|---|
| pre-commit | `tools/githooks/pre-commit` | 文档一致性、音频二进制阻断、模糊命名阻断、根目录反杂乱、轻量敏感信息扫描 | `.github/workflows/quality-gates.yml` 调用 `tools/scripts/run_quality_gates_ci.sh`，执行与 pre-commit 对应检查 | 1) 对照 `pre-commit` 中 5 项规则与 `run_quality_gates_ci.sh` 的 5 个检查段落；2) 在 PR 中附 CI 日志，确认 5 项均执行；3) 任一规则变更时，同步更新 Hook 与 CI 脚本并复核 |
| commit-msg | `tools/githooks/commit-msg` | `type(scope): summary` 正则校验（允许 Merge/Revert 自动消息） | CI 对应为提交标题/PR 标题格式校验（与 `commit-msg` 使用同一正则语义） | 1) 以 `tools/githooks/commit-msg` 的正则为唯一来源；2) 对照 CI 中标题校验规则与 Hook 正则一致；3) 在审计记录中标记“commit-msg ↔ CI 标题校验”同源结果 |
| pre-push | `tools/githooks/pre-push` | 快速测试门禁（Python `pytest -q` / Node `npm test -- --watch=false`，按可用栈执行） | `.github/workflows/quality-gates.yml` 中 `quality-gates` 任务执行 `run_quality_gates_ci.sh` 的快速测试段落 | 1) 对照 `pre-push` 快速测试命令与 CI 脚本命令一致；2) 抽样比对本地与 CI 的测试入口命令；3) 变更测试入口时同一 PR 同步修改 Hook 与 CI |

## C. 同源判定标准
1. 每个 Hook 都有明确 CI 镜像项（`pre-commit` / `commit-msg` / `pre-push` 不可缺失）。
2. 每个镜像项都能指向唯一来源文件（SoT）并提供可复核命令或日志路径。
3. Hook 与 CI 任一侧规则发生变更，必须在同一变更中更新本清单并完成一次对照验证。

## D. 审计最小证据
- Hook 来源：`tools/githooks/*` 对应片段。
- CI 来源：`.github/workflows/quality-gates.yml` 与 `tools/scripts/run_quality_gates_ci.sh` 对应片段。
- 复核结果：同一条检查在本地与 CI 均可定位、可执行、可追溯。
