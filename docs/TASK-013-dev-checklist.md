# TASK-013 · 终结循环 · 三杠杆瘦身整改 — 开发执行清单

## 版本信息
- **任务编号**: TASK-013
- **状态**: 待执行（一次性交付，中途不提审）
- **前置冻结**: 冻结一切新功能 48 小时；先把 TASK-010/011/micro-fix 合并成 v2.2 单一 spec，删除过期注释
- **目标**: 系统从"偶尔过 9/9"变成"稳定过 9/9"

---

## 一、为什么越修越烂（冷诊断）

1. **R18 把"演唱"当成"打字"**。103 BPM 下副歌多 1 字，歌手用切分/三连一带就过；规则却判 HARD_FAIL，逼模型为 1 字毁一句。
2. **revise prompt 是"局部手术"指令**。输入是"第 X 行超 1 字"，模型只会删字、倒装、凑韵——这不是模型能力差，是你给它的环境只允许它做这种烂选择。
3. **同模型反复修自己写的东西**。没有"换脑子"，第 3 次只是第 1 次的劣化版。
4. **PM Rule 第八条 `llm_calls<=2` 是制度死结**。你想多调一次审校都违规，于是只能在 2 次之内硬修，于是必出倒装。
5. **几天连续 patch，确实在垃圾上叠垃圾**。但叠出来的是 profile router / lint / hooks / TDD 等**结构性资产**，主干没烂，烂的是末端两个文件：`lint.py R18 分支` + `revise_prompt`。

---

## 二、要不要推倒重写？

**不要。** 推倒重写在当前状态下 = 第 4 次叠垃圾。

判断依据：
- 主链 DAG（retriever → router → SKILL → 主生成 → lint → revise → audit）方向是对的
- profile 一等公民、corpus 多元化、hooks/TDD、run-id 隔离——这些都是耐久资产
- 失败集中在两个点：R18 的边界判定 + revise 的提示语策略。**这是末端 bug，不是架构 bug**

要做的不是重构，是**瘦身回归**：把 TASK-010 / 011 / micro-fix 合并落到 v2.2 单一规范，删掉过期 patch 注释，让团队停下来做一次"清账"，然后才动这次的修复。

---

## 三、最小维度修复方案（三杠杆，零新模块）

### 杠杆 1 — R18 语义重定义（改 lint 一个分支）

| 条件 | 现行 | 新规则 |
|------|------|--------|
| 非韵脚行 ±1 字 | HARD_FAIL | **SOFT_PASS** · 自动打 `[Syncopation]` / `[Triplet]` 标签 |
| 韵脚行 ±1 字 | HARD_FAIL | HARD_FAIL（保留） |
| ±2 字及以上 | HARD_FAIL | HARD_FAIL（保留） |

**预计直接消灭 60–70% 当前失败。** 不调模型，不写新规则，只改一个判定分支。这一步必须先做，否则后面所有努力都被 1 字阻断。

**改动范围**: `src/lint.py` 的 R18 单一分支 + lint_report 字段 `soft_pass_with_annotation`

### 杠杆 2 — revise prompt 从"补丁"升维成"段落重生"

现行 prompt 心智："你超了 1 字，删一个。"

新 prompt 心智："保留情绪锚点 [水壶冷了 / 承认无常]，韵脚 [ang]，**整段推倒，用 budget=12 重写**。严禁倒装、严禁删字凑韵；若原意象达不到，**换意象**。"

关键差异：
- 输入单位：行 → **段**
- 自由度：改字 → **重写句式 + 可换意象**
- 红线：**显式禁止倒装/凑韵**（写进 prompt，不靠默契）
- 锚点：保留情绪关键词清单，确保不漂移

**改动范围**: `fragments/*.md` 中的 revise 段 + `revise_prompt.md`（如有独立文件）

### 杠杆 3 — 异构审校 +1 次调用（接受 `llm_calls<=4`）

调用预算分层（封顶 4，不无限）：

1. **Call#1** 主生成（3 variants）
2. **Call#2** 段落级 revise（杠杆 2 的新 prompt）
3. **Call#3** 异构审校（**低 temperature 的另一家模型**，唯一职责：扫倒装/拗口/凑韵，**字数不许动**）
4. **Call#4** 仅当 #3 仍标红时的最后一次段落重写；之后 fail-loud，绝不静默放行

trace 必须记录：`call_stage` / `model_used` / `quality_delta`，让你眼见为实。

**改动范围**: `src/main.py` 调用链 + `src/claude_client.py`（新增审校调用）+ trace 字段扩展

---

## 四、制度阻塞必须先解（否则上面全是空话）

PM Rule 当前两条与新方案直接冲突，必须正式改：

| 现行条款 | 改为 | 理由 |
|----------|------|------|
| 法则一 / 法则八：`llm_calls <= 2` | `llm_calls <= 4`，分层封顶 | 已确认"不在乎次数，要最终质量" |
| 法则三：lint 只评分不放行草稿 | 增"SOFT_PASS 类目 + 演唱标签注入"豁免 | 给 R18 弹性合法身份 |

**不改 PM Rule，开发就是违规交付，pm-audit 永远不会绿。** 这是当前死循环的真正根源之一。

**改动范围**: `docs/🎵 AI 音乐生成系统产品经理 (PM) Role & Rule.md`

---

## 五、执行清单（逐项打卡）

### Step 0 — 清账回归（必须先做）
- [ ] 合并 TASK-010/011/micro-fix 到 v2.2 单一 spec
- [ ] 删除 `src/lint.py`、`src/main.py` 中所有过期 patch 注释
- [ ] 删除未使用的临时文件和测试数据
- [ ] 验证 `pytest -q` 仍通过（基线）

### Step 1 — R18 弹性化
- [ ] 修改 `src/lint.py` R18 判定逻辑
  - [ ] 非韵脚行 ±1 字：HARD_FAIL → SOFT_PASS
  - [ ] SOFT_PASS 时自动注入 `[Syncopation]` 或 `[Triplet]` 标签到 voice_tags_inline
  - [ ] 韵脚行 ±1 字：保持 HARD_FAIL
  - [ ] ±2 字及以上：保持 HARD_FAIL
- [ ] lint_report 新增 `soft_pass_with_annotation` 字段记录此类豁免
- [ ] **先写失败测试**（用 ±1 字非韵脚行场景），再写实现
- [ ] 运行 `pytest tests/test_lint_r18.py -q` 验证

### Step 2 — revise prompt 升维
- [ ] 重写 revise prompt 模板（行级补丁 → 段级重生）
  - [ ] 明确输入单位：整段（section）而非单行
  - [ ] 强制保留锚点：情绪关键词 + 韵脚约束
  - [ ] 显式红线：禁止倒装、禁止删字凑韵、禁止语气词凑韵尾
  - [ ] 允许策略：可换意象、可调整句式结构
- [ ] 更新 `src/main.py` 中 `_build_targeted_revise_prompt` 函数
- [ ] **先写失败测试**（用当前 prompt 产生倒装的场景），再写实现
- [ ] 运行 `pytest tests/test_revise_prompt.py -q` 验证

### Step 3 — 异构审校 Call#3
- [ ] 修改 `src/main.py` 调用链
  - [ ] 在 Call#2 revise 后增加 Call#3 审校调用
  - [ ] 审校调用使用低 temperature（如 0.2）
  - [ ] 审校职责仅限于：扫倒装/拗口/凑韵，**不改动字数**
  - [ ] 审校结果触发 Call#4（仅当仍有 R03/R14/R16 类问题时）
- [ ] 修改 `src/claude_client.py` 或创建审校专用调用函数
- [ ] trace 新增字段：`call_stage`、`model_used`、`quality_delta`
- [ ] **先写失败测试**，再写实现
- [ ] 运行 `pytest tests/test_heterogeneous_review.py -q` 验证

### Step 4 — PM Rule 同步修订
- [ ] 修改 `docs/🎵 AI 音乐生成系统产品经理 (PM) Role & Rule.md`
  - [ ] 法则一/八：`llm_calls <= 2` → `llm_calls <= 4` 分层封顶
  - [ ] 法则三：增 SOFT_PASS 豁免条款说明
  - [ ] 法则十一/十二：保持已有内容
- [ ] 运行 `docs-check` 验证一致性

### Step 5 — 全量回归验证
- [ ] `python -m pytest -q` → 全绿（允许已知 xfail）
- [ ] `python -m apps.cli.main gate-check --all`
  - [ ] G0-G6 必须 pass
  - [ ] G1 若为 commit_scope_gate 策略噪音，单列说明
- [ ] `python -m apps.cli.main pm-audit` → TOTAL: 9, PASS: 9
- [ ] `docs-check` → OK
- [ ] **关键验证**：连续 5 次 E2E（同主题不同 seed）必须 5/5 拿到 9/9
- [ ] 关键 run-id trace 证据完整（含 call_stage、fail_reasons）

---

## 六、红线（不可逾越）

1. **不增中间件**（不引入向量数据库、embedding 模型等）
2. **不增依赖**（不新增 pip 包）
3. **不重构主链**（retriever → router → SKILL → 主生成 → lint → revise → audit 保持不变）
4. **不允许第 5 次调用**（封顶 4 次，第 4 次后 fail-loud）
5. **不修改已稳定的 profile 路由逻辑**
6. **TDD 优先**：每条改动必须先写失败测试再写实现
7. **证据先于结论**：无命令输出 = 未完成

---

## 七、提交规范

- **单分支统一开发**：使用当前分支 `fix/issue32-rhyme-monotony-corpus-routing`
- **单一干净 commit**：所有修改合并为一个 commit
- **Commit message 模板**：
  ```
  fix(task013): R18 elastic threshold + revise prompt rebirth + heterogeneous review
  
  - R18: non-rhyme ±1 char SOFT_PASS with auto [Syncopation]/[Triplet] tags
  - revise: line-patch → section-rebirth, explicit anti-chiasmus/anti-filler redlines
  - Call#3: low-temp heterogeneous review for prosody only (no word count change)
  - PM Rule: llm_calls cap raised from 2 to 4 with tiered budget
  - TDD: all changes preceded by failing tests
  ```
- **PR 描述必须包含**：
  1. 变更映射（Step 0-5 → 文件清单）
  2. 命令证据原样粘贴
  3. 连续 5 次 E2E 9/9 截图/日志
  4. 回滚方案（按 commit 粒度）

---

## 八、验收标准（PM 终审）

功能正确 + 证据完整 + 无策略外回归 = 可放行

如出现以下任一情况，直接驳回：
- 中途提审、分段要口头绿灯
- 目录污染（未清理的临时文件）
- 无测试覆盖的改动
- 口头结论、无命令输出
- 连续 5 次 E2E 未达 5/5 的 9/9

---

## 九、开发口令

```bash
# 1. 先清账回归
python -m pytest -q  # 确认基线通过

# 2. 按 Step 1-5 逐项执行
# 每步：先写测试（失败）→ 写实现（通过）→ 提交临时 commit

# 3. 最终验证
python -m pytest -q
python -m apps.cli.main gate-check --all
python -m apps.cli.main pm-audit --run-id <your_run_id>
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/check_docs_consistency.ps1"

# 4. 连续 5 次 E2E 验证（同主题不同 seed）
for i in 1 2 3 4 5; do
  python -m apps.cli.main produce "你的测试主题" --seed $i --out-dir out/runs/e2e_test_$i
done
# 检查每个 out/runs/e2e_test_*/trace.json 的 pm_audit 结果

# 5. 合并为单一 commit 并推送
git add .
git commit -m "fix(task013): R18 elastic threshold + revise prompt rebirth + heterogeneous review"
git push origin fix/issue32-rhyme-monotony-corpus-routing
```

---

## 十、为什么这版能稳

- **R18 弹性化** = 砍掉最大一类伪失败（约 70%）
- **revise 升维** = 砍掉倒装/凑韵这种"为合规毁艺术"的输出（剩 20%）
- **异构审校** = 给最后 10% 兜底，且换脑子真的有效
- **PM Rule 同步修订** = 制度不再卡住技术
- **冻结+瘦身回归** = 阻止"垃圾叠垃圾"的工程债继续滚雪球

不重构、不加模块、不加依赖，三个文件 + 一份 spec 修订，结束这场拉锯。
