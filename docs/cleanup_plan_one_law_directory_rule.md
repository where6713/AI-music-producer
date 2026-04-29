# 文件收敛清理计划（Dry Run）

适用法则：`one law.md`、`目录框架规范.md`  
适用范围：`G:\AI-music-producer`  
执行方式：**仅清理计划，不执行删除**（本文件用于 PM 复审）

---

## 1. 目标与边界

- 目标：在不破坏主链路（`python -m apps.cli.main produce`）前提下，降低冗余维护面，收敛唯一事实源。
- 边界：本次仅提交清理清单与执行顺序，不做删除操作。

---

## 2. 分类规则（引用法则）

1. 可验证性优先：每一项清理必须能通过命令验证（测试、审计、门禁）。
2. 单一归属：规范正文必须有唯一 owner 文件，非 owner 仅保留引用。
3. 职责边界：
   - `src/` 放业务逻辑
   - `tools/scripts/` 放工程辅助
   - `docs/` 放当前有效规范
4. 不引入新中间件、不扩展复杂流程。

---

## 3. 清理清单（候选）

### A 类：立即可删（临时/缓存/非资产）

1. `.pytest_cache/`
2. `.ruff_cache/`
3. `.tmp/`
4. `.sisyphus/`
5. `.worktrees/`（仅删除已确认孤儿路径，禁止整目录一刀切）
6. 全仓 `__pycache__/`

说明：A 类不涉及业务事实，不影响主链路语义。`worktrees` 必须逐路径执行安全检查后再删。

### B 类：文档收敛（唯一归属）

保留 owner：

1. `docs/映月工厂_极简歌词工坊_PRD.json`
2. `one law.md`
3. `目录框架规范.md`
4. `docs/ai_doc_manifest.json`
5. `docs/runbook_cli_commands.md`

候选合并后删除：

1. `docs/issue19_task_evidence.md`
2. `docs/issue20_pm_audit_evidence.md`
3. `docs/task013_contract_v1.md`
4. `docs/开发整改事项清单.md`

整改任务文档收敛：

1. `docs/整改task.json`
2. `docs/整改task - 02.json`
3. `docs/整改task-013-ref-audio-pipeline.json`

建议：三者收敛为单一“当前任务索引 + 历史归档链接”。

### C 类：技能文档去重

保留：`.claude/skills/` 作为唯一技能源。  
候选删除：

1. `skills/CLAUDE.md`
2. `skills/SKILLS.md`

前提：确认无外部流程硬依赖根目录 `skills/`。

### D 类：脚本职责去重

现状：`scripts/` 与 `tools/scripts/` 均存在工程脚本，职责边界重叠。  
候选动作：

1. 业务判断脚本回迁 `src/`
2. 工程辅助脚本统一归档 `tools/scripts/`
3. 重复脚本合并后删除旧副本

重点复核文件：

1. `scripts/run_corpus_ingestion.py`
2. `scripts/merge_raw_to_corpus.py`
3. `scripts/repair_golden_rows.py`
4. `scripts/auto_tag_golden_anchors.py`

---

## 4. 执行顺序（DAG）

1. 先执行 A 类（低风险）
2. 再执行 B 类（文档归属）
3. 再执行 C 类（技能去重）
4. 最后执行 D 类（脚本迁移）

任何一步失败，停止并回滚当前步。

每步执行纪律：

1. 先快照（目录清单 + `git worktree list`）
2. 先验证（见第 5 节步进门）
3. 再执行当前步动作
4. 再验证并留档（命令原文 + 输出摘要）

---

## 5. 验证命令（每步后必跑）

```powershell
python -m pytest -q
python -m apps.cli.main pm-audit
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/check_docs_consistency.ps1"
```

验收口径：

- 功能测试不过：不进入下一步
- 文档一致性不过：不进入下一步
- 审计输出需完整留档

门禁分层：

1. **步进门（每步执行）**：`pytest -q`、`pm-audit`、docs consistency
2. **收口门（阶段末执行）**：`python -m apps.cli.main gate-check --all`
   - 若 `G1` 因仓库策略（`commit_scope_gate`）失败，单独标注为策略门未闭环，不得伪装成功能回归。

### 5.1 worktree 清理安全流程（强制）

删除任何 worktree 前必须逐项执行：

```powershell
git worktree list
git -C "<worktree_path>" status --short
```

仅当目标路径状态为空（无改动）时，允许删除：

```powershell
git worktree remove "<worktree_path>"
git worktree list
```

若 `status --short` 非空：禁止删除，先迁移或提交该工作区改动。

---

## 6. 风险与回滚

- 风险 1：删除文档导致引用断裂
  - 回滚：恢复文档并修 manifest
- 风险 2：脚本迁移导致调用路径失效
  - 回滚：恢复原路径并追加兼容入口
- 风险 3：技能源切换导致加载失败
  - 回滚：恢复 `skills/` 并补充引用说明

---

## 7. 结论

本计划满足“先法则、后实现；先校验、后扩展”的顺序要求。  
当前状态：**仅计划，未执行删除**，等待 PM 复审后按步骤落地。
