# 证据规范（计划证据 / 执行证据 / 验证证据）

> 目标：拒绝“口头完成”，统一用可复跑、可审计的文本证据判定完成度。  
> 上位约束：`one law.md`、`开发清单.md`、`docs/governance/gates.md`。

## 1) 三类证据定义（字段规范 + 路径规范 + 命名规范）

### A. 计划证据

**字段规范（必填，缺一视为无效）**
- `gate`: 证据对应 gate（如 `G1`）
- `task`: 任务编号（如 `task-04`）
- `status`: `done` / `failed`
- `prd_source`: PRD/清单映射来源（必须可定位）
- `objective`: 单步目标（只允许一个明确结果）
- `input`: 输入定义（现有文件、脚本、上下文）
- `output`: 输出定义（目标文件/产物）
- `completion`: 可执行完成判定语句（命令或可验证条件）

**存储路径**
- 固定存储路径：`.sisyphus/evidence/`

**命名规范**
- 文件名：`task-{编号}-plan-{说明}.txt`
- 示例：`task-04-plan-prd-mapping.txt`

---

### B. 执行证据

**字段规范（必填，缺一视为无效）**
- `gate`: 证据对应 gate（如 `G2` / `G3`）
- `task`: 任务编号
- `status`: `done` / `failed`
- `command logs`: 实际执行命令与关键输出（原始文本）
- `test logs`: 测试日志摘要（必须体现 red/green 或失败原因）
- `decision`: 执行后决策（继续/回滚/修复）
- `pass_or_fail`: `pass` / `fail`

**存储路径**
- 固定存储路径：`.sisyphus/evidence/`

**命名规范**
- 文件名：`task-{编号}-exec-{说明}.txt`
- 示例：`task-04-exec-red-log.txt`、`task-04-exec-green-log.txt`

---

### C. 验证证据

**字段规范（必填，缺一视为无效）**
- `gate`: 证据对应 gate（如 `G4`~`G8`）
- `task`: 任务编号
- `status`: `done` / `failed`
- `command logs`: 复核命令与输出（独立于执行记录）
- `decision`: 通过/驳回结论与原因
- `pass_or_fail`: `pass` / `fail`
- `rollback_point`（当 `pass_or_fail=fail` 必填）: 最近可回滚状态

**存储路径**
- 固定存储路径：`.sisyphus/evidence/`

**命名规范**
- 文件名：`task-{编号}-verify-{说明}.txt`
- 示例：`task-04-verify-gate-g4.txt`

## 2) 通用格式约束

- 统一使用 UTF-8 文本（`.txt`），禁止图片、截图替代原始日志。
- 所有字段键名使用英文小写（与现有 gate 解析一致），内容可中英文。
- 证据文件必须可被 `Select-String` / gate 脚本直接解析。
- 单任务至少包含：`1份计划证据 + 1份执行证据 + 1份验证证据`。

## 3) 防作弊与可验证机制

### 3.1 交叉一致性校验（强制）
- 校验关系：`计划证据.objective` ↔ `执行证据.command logs/test logs` ↔ `验证证据.decision`。
- 规则：三者目标与结论不一致时，整组证据判定为无效。

### 3.2 原始日志约束（强制）
- 必须保留可复制的原始命令与输出文本；禁止“仅结论无日志”。
- 对关键步骤（测试、gate、构建）至少记录一条可复跑命令。

### 3.3 抽样复跑（强制）
- 验证阶段至少抽查 1 条执行命令复跑，输出需与执行证据结论一致。
- 若复跑不一致，`pass_or_fail` 必须为 `fail`，并填写 `rollback_point`。

### 3.4 身份与时序合理性校验（建议落地）
- 证据应按 `plan -> exec -> verify` 时序生成，不允许验证证据早于执行证据。
- 文件名任务号必须一致（例如 `task-04-*`），防止跨任务拼接伪造。

## 4) 失败处理

1. 产出失败证据（`status: failed` + `pass_or_fail: fail`）。
2. 在验证证据中记录 `rollback_point`。
3. 回滚到最近可验证状态后重新执行。
4. 重新提交三类证据并再次进入 gate 校验。
