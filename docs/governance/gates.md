# Gate 清单（G0-G7）

> 目标：把“完成”定义为可执行命令 + 可复验证据。
> 规则：任一 Gate 不通过即停止推进，不允许跳过或口头放行。

## G0 环境与 Hook 链门禁
- 输入：本地仓库、`tools/githooks/*`、`开发清单.md`
- 检查器：
  - `git config --get core.hooksPath`
  - `Test-Path 'tools/githooks/pre-commit'; Test-Path 'tools/githooks/commit-msg'; Test-Path 'tools/githooks/post-commit'; Test-Path 'tools/githooks/pre-push'`
  - `Select-String -Path '开发清单.md' -Pattern '先测试，后实现|先通过 Hook，再允许流程扩张'`
- 通过条件：`core.hooksPath` 等于 `tools/githooks`；四个 hook 文件均存在；开发清单中存在 Hook 与 TDD 约束语句。
- 失败处理：执行 `powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/install_hook_chain.ps1"` 修复；修复后重跑 G0 全部检查。

## G1 变更范围与提交规范门禁
- 输入：本次变更文件列表、提交首行信息
- 检查器：
  - `git diff --name-only --cached`
  - `Select-String -Path '.git/COMMIT_EDITMSG' -Pattern '^(feat|fix|docs|refactor|test|chore|build|ci|perf|revert)\([a-z0-9._/-]+\): .+'`
  - `Select-String -Path 'tools/githooks/pre-commit' -Pattern 'ROOT_WHITELIST_REGEX|AKIA\[0-9A-Z\]\{16\}|BEGIN PRIVATE KEY|api\[_-\]\?key'`
- 通过条件：提交首行匹配 `commit-msg` 规则；未命中 root 白名单违例、密钥规则、音频二进制规则。
- 失败处理：修正提交信息或暂存内容后重新 `git commit`，不得使用 `--no-verify`。

## G2 Red 证据门禁
- 输入：失败测试日志（建议文件：`.sisyphus/evidence/task-*-exec-red-log.txt`）
- 检查器：
  - `Test-Path '.sisyphus/evidence'`
  - `Select-String -Path '.sisyphus/evidence/task-*-exec-red-log.txt' -Pattern 'FAILED|AssertionError|E\s+\w+'`
  - 运行目标测试命令并记录非零退出码（示例：`python -m pytest <target_test> -q`，`$LASTEXITCODE -ne 0`）
- 通过条件：存在可读取的 Red 日志；日志包含失败断言/失败用例；目标测试命令退出码非 0。
- 失败处理：补齐 Red 用例与日志后再进入实现；禁止在 G2 未通过时改业务实现。

## G3 Green 证据门禁
- 输入：实现变更、通过测试日志（建议文件：`.sisyphus/evidence/task-*-exec-green-log.txt`）
- 检查器：
  - 运行目标测试命令并记录零退出码（示例：`python -m pytest <target_test> -q`，`$LASTEXITCODE -eq 0`）
  - `Select-String -Path '.sisyphus/evidence/task-*-exec-green-log.txt' -Pattern 'passed|ok|0 failed'`
  - `git diff --name-only` 与任务范围比对
- 通过条件：目标测试退出码为 0；Green 日志包含通过标记；变更范围不超出任务边界。
- 失败处理：回退到 G2，先恢复可复现的失败->通过闭环，再继续。

## G4 文档一致性门禁
- 输入：文档变更（`docs/**`）
- 检查器：`powershell -NoProfile -ExecutionPolicy Bypass -File 'tools/scripts/check_docs_consistency.ps1'`
- 通过条件：脚本退出码为 0，且输出不含 `FAIL` / `ERROR`。
- 失败处理：按脚本输出逐项修正文档并重跑脚本，未通过前禁止提交。

## G5 提交前 Hook 执行门禁
- 输入：本次提交（staged changes）
- 检查器：
  - 执行 `tools/githooks/pre-commit`
  - 执行 `tools/githooks/commit-msg`
  - `Select-String -Path 'tools/githooks/pre-commit' -Pattern '\\.(wav|mp3|flac|ogg|aac|m4a)\$|temp|new|utils|helper'`
- 通过条件：pre-commit 与 commit-msg 均返回成功状态；无命名违例、音频二进制违例、密钥违例。
- 失败处理：按 hook 报错修复后重试 commit；禁止 `--no-verify`。

## G6 推送前门禁
- 输入：待推送提交、`.git/oost-hook-ledger`
- 检查器：
  - 执行 `tools/githooks/pre-push`
  - `Test-Path '.git/oost-hook-ledger'`
  - `git rev-parse HEAD` 后检查 ledger 是否存在 `<commit_hash> verified`
- 通过条件：pre-push 返回成功；ledger 存在且当前 HEAD 记录为 `verified`；快速测试链通过（pytest/npm test 条件触发时均通过）。
- 失败处理：执行一次不带 `--no-verify` 的修复提交（必要时 `git commit --amend --no-edit`），再重跑 pre-push。

## G7 Gate 总闭环门禁
- 输入：Gate 证据文件、任务验证命令输出
- 检查器：
  - `powershell -NoProfile -ExecutionPolicy Bypass -File 'tools/scripts/next_gate.ps1' -TaskId '<task-id>' -Json`
  - `Select-String -Path '.sisyphus/evidence/task-<task-id>-*.txt' -Pattern 'status:\s*done|pass_or_fail:\s*pass|test logs|command logs'`
  - `Test-Path 'docs/governance/gates.md'`
- 通过条件：`next_gate` 输出 `nextGate: DONE`；证据字段完整且非空；治理文档存在并可检索到 Gate 字段关键词。
- 失败处理：按缺失项补证据并回到失败 Gate 重跑；`nextGate != DONE` 时禁止声明任务完成。

---

## 统一失败处理
1. 记录失败 Gate、命令、退出码、证据路径。
2. 回滚到最近一次可复验状态（代码 + 文档 + 证据）。
3. 仅修复导致失败的最小变更，再次执行该 Gate 检查器。
4. 当前 Gate 通过后，按顺序继续下一个 Gate。
