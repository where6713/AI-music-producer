# TASK-013 Contract v1（可下发）

## 决策快照

- R18 严重度：`HARD_PENALTY`（温和）
- 对称阈值：段内字数极差 `> 2` 判失败（更宽）
- 执行顺序：定文本 -> 定白名单 -> 定 lint -> 定 audit -> 再进入实现 PR

## 1) Prompt Contract（Prosody Alignment）

### 1.1 输入变量

- `{{bpm}}`
- `{{syllable_budget_min}}`
- `{{syllable_budget_max}}`
- `{{active_profile}}`

### 1.2 规则定义

1. **结构对称**
   - 在同一段落内（如 `[Verse 1]` / `[Chorus]`），行字数极差要求 `<= 2`。
   - 若 `> 2`，触发 R18 失败（见 Lint Contract）。

2. **字数预算约束**
   - 单句实体中文字数必须落在 `{{syllable_budget_min}}` 到 `{{syllable_budget_max}}` 区间。
   - 预算边界触发元标签导演（见 1.3）。

3. **结构锚点**
   - 必选：`[Verse 1]`, `[Verse 2]`, `[Chorus]`, `[Bridge]`, `[Outro]`
   - 条件可选：`[Pre-Chorus]`, `[Drop]`, `[Beat Break]`

### 1.3 元标签导演触发器

- 当 `len(line) <= {{syllable_budget_min}}`：必须加入 pause 类标签（白名单内）
- 当 `len(line) >= {{syllable_budget_max}}`：必须加入 fast 类标签（白名单内）

## 2) Tag Whitelist Contract

### 2.1 Pause 类白名单

- `(Breathe)`
- `(Pause)`
- `(...)`

### 2.2 Fast 类白名单

- `[Fast Flow]`
- `[Staccato]`
- `[Rapid]`

### 2.3 结构标签白名单

- `[Verse 1]`, `[Verse 2]`, `[Chorus]`, `[Bridge]`, `[Outro]`, `[Pre-Chorus]`, `[Drop]`, `[Beat Break]`

### 2.4 Profile 标签权限矩阵

- `club_dance`：允许 `[Drop]`、`[Beat Break]`
- `urban_introspective`：默认不允许 `[Drop]`，可用 `[Pre-Chorus]`
- `classical_restraint`：默认不允许 `[Drop]`、`[Beat Break]`
- `uplift_pop`：默认不允许 `[Drop]`，可用 `[Pre-Chorus]`
- `ambient_meditation`：默认不允许 `[Drop]`、`[Beat Break]`

> 说明：非白名单标签视为 OOV，进入拦截/替换流程。

## 3) Lint Contract（R18）

### 3.1 规则定义

- `rule_id`: `R18`
- `name`: `prosody_alignment_gate`
- `severity`: `HARD_PENALTY`

### 3.2 触发条件

任一条件满足即触发 R18：

1. 同段落行字数极差 `> 2`
2. 行字数严重偏离 `ProsodyMatrix` 预算区间（超出容差）

### 3.3 触发动作

- 标记 variant 为 `R18 failed`
- 进入扣分与排序逻辑（不直接 `is_dead=true`）
- 若触发后 chosen 低于质量线，走 Targeted Revise

## 4) Audit Contract

### 4.1 trace/audit 必备字段

- `prosody_matrix_used`
- `prosody_alignment_delta_max`
- `prosody_tag_injection_count`
- `ref_audio_fallback_used`
- `ref_audio_fallback_reason`

### 4.2 pm-audit 新增检查项（第 9 项）

- `check_key`: `prosody_matrix_aligned`
- 判绿条件：
  - 使用 `--ref-audio` 时，存在可审计的 ProsodyMatrix 记录
  - 段内极差符合阈值（`<=2`）
  - 标签注入符合白名单策略

## 5) 实施前闸门（Go/No-Go）

只有在以下合同同时冻结后，才允许进入 PR-013-01~07 代码实现：

1. Prompt Contract 冻结
2. Whitelist Contract 冻结
3. R18 Contract 冻结
4. Audit Contract 冻结

---

本文件用于开发代理直接执行，不含实现代码，仅定义不可歧义的契约与验收口径。
