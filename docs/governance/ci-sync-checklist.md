# CI 与本地 Hooks 同源清单

> 原则：本地过 = CI 过；本地不过 = CI 不过。

## A. 当前本地检查项（来自 hooks）

### pre-commit
- 文档一致性脚本
- 禁止提交音频二进制
- 禁止模糊脚本命名
- 根目录反杂乱
- 轻量敏感信息扫描

### commit-msg
- `type(scope): summary` 提交信息格式校验

### pre-push
- 快速测试（Python/Node 可用时执行）

## B. CI 镜像要求
- [ ] CI 必须执行与 pre-commit 等价的检查
- [ ] CI 必须执行与 commit-msg 等价的格式校验（PR 标题或 squash commit）
- [ ] CI 必须执行与 pre-push 等价的测试集合
- [ ] CI 输出日志路径可追溯并可用于审计

## C. 同源清单（逐项对照）
| 检查项 | 本地 hook | CI Job | 状态 |
|---|---|---|---|
| 文档一致性 | pre-commit | ci-doc-consistency | 待建立 |
| 音频二进制阻断 | pre-commit | ci-binary-guard | 待建立 |
| 命名规范检查 | pre-commit | ci-naming-guard | 待建立 |
| 根目录反杂乱 | pre-commit | ci-root-hygiene | 待建立 |
| 敏感信息扫描 | pre-commit | ci-secret-scan | 待建立 |
| 提交格式校验 | commit-msg | ci-commit-format | 待建立 |
| 快速测试 | pre-push | ci-quick-tests | 待建立 |

## D. 变更流程
1. 先改本地检查或 CI 检查中的一处
2. 同步更新同源清单
3. 在同一变更中补齐另一处
4. 执行一次“本地+CI”对照验证

## E. 通过判定
- 同源清单无“待建立”项（或已登记延期并说明原因）
- 任一检查项在本地与 CI 的结果一致
