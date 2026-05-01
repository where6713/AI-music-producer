# 修复流程决策树（Repair Decision Tree）

## 目标
把“偶尔过 9/9”变成“稳定过 9/9”，同时保证：
- 失败时 **fail-loud + 明确原因**，绝不静默空结果回用户
- 默认 2 次调用；仅 R18/R19 允许第 3 次；总上限 4 次
- 不新增中间件/依赖，不重构主链路

---

## 决策树（总览）

```
Call #1 主生成（3 variants）
    ↓
Lint → 全过？→ 输出
    ↓ 有失败
仅 R18/R19？→ 是 → Call #2 段级重生 revise
    ↓ 否              ↓
HARD_KILL？→ 是 → REJECTED（fail-loud）
    ↓ 否              ↓
Craft < 0.85？→ 是 → Call #2 段级重生 revise
    ↓ 否
输出 best draft（warning）

Call #2 后：
    ↓
Lint → R18/R19 仍在？→ 是 → Call #3 异构审校（低 temp，只审语感/倒装/凑韵，不改字数）
    ↓ 否或已过
输出

Call #3 后：
    ↓
审校发现仍有 R18/R19 类问题？→ 是 → Call #4 最终段级重生
    ↓ 否
输出

Call #4 后：
    ↓
仍有 R18/R19？→ 是 → REJECTED（fail-loud，附 trace 证据）
    ↓ 否
输出
```

---

## 三级修复策略

### L1 — 局部修（Local Patch）
**触发条件**：
- 失败规则集 ⊆ {R01, R05, R06}（结构性微调）
- 或 craft_score ≥ 0.85 且仅少量 SOFT_PENALTY

**策略**：
- 输入单位：单行
- 仅修改失败行，其余行原样保留
- 适用 prompt：现行 targeted revise（行级补丁）

**不做的事**：
- 不重构段落
- 不换意象
- 不倒装、不删字凑韵

---

### L2 — 段级重生（Section Rebirth）
**触发条件**：
- 失败规则含 R18 或 R19
- 或 craft_score < 0.85 且非 HARD_KILL

**策略**：
- 输入单位：整段（section），而非单行
- 保留情绪锚点（emotional_register + core_tension + 关键意象词）
- 保留韵脚约束（同段韵母一致）
- **红线**：
  - 严禁倒装（把介词/连词甩到句尾）
  - 严禁凑韵（用语气词 啊/哦/呢/嘛/嗯/哟/啦/哼/哈/哎/吖/呵/噢/喔/呀/哇/吧/吗 等做韵尾）
  - 严禁删字硬压预算（宁可换意象，不可毁语义）
- **允许策略**：
  - 可换意象（用同情绪等价意象替换）
  - 可调整句式结构（主谓宾重新排列，但保持语义完整）
  - 可在 voice_tags_inline 注入演唱提示（[Syncopation] / [Triplet]）

**输出契约**：
- 必须输出完整 3 variants JSON
- 未修改段落原样保留
- 字段覆盖：few_shot_examples_used, distillation, structure, lyrics_by_section, variants, chosen_variant_id, style_tags, exclude_tags

---

### L3 — 异构审校（Heterogeneous Review）
**触发条件**：
- Call #2 后 R18/R19 仍然存在
- llm_calls 当前 = 2

**策略**：
- 调用模型：**同一模型，temperature = 0.2**（低创造力，高一致性）
- 输入：Call #2 输出的最佳 variant 歌词全文
- 职责：
  1. 扫倒装（句尾是被/把/将/让/而/却/但/且/并 等残缺介词/连词）
  2. 扫拗口（连续同音字、绕口令式堆砌）
  3. 扫凑韵（语气词堆叠、同一字重复做韵尾 ≥4 次）
  4. **不改字数**（只标问题，不动文本）
- 输出：JSON 问题清单，每条含 `{section, line, issue_type, suggestion}`

**不做的事**：
- 不生成新歌词
- 不改字数
- 不动意象
- 不处理 R03/R14/R16（内容 hazard 已在 Call #1/2 解决）

---

### L4 — 最终段级重生（Final Rebirth）
**触发条件**：
- Call #3 审校发现仍有 R18/R19 类问题
- llm_calls 当前 = 3

**策略**：
- 同 L2，但 prompt 追加：
  - “这是最后一次修改机会，请确保输出可直接交付。”
  - “若仍无法解决，请明确标注 `[UNFIXABLE]` 并说明原因。”

**终止条件**：
- Call #4 后仍有 R18/R19 → **REJECTED**（fail-loud）
- 不允许 Call #5

---

## R18 弹性规则（Lint 判定）

| 条件 | 结果 | 动作 |
|------|------|------|
| 非韵脚行，超预算 1 字 | SOFT_PASS | 不记 violation，但 lint_report 标注 `soft_pass_annotations`，主链路注入 `[Syncopation]` 或 `[Triplet]` 到对应 section 的 voice_tags_inline |
| 韵脚行，超预算 1 字 | HARD_FAIL | 记 violation，触发 revise |
| 超预算 ≥2 字 | HARD_FAIL | 记 violation，触发 revise |

**韵脚行判定**：
- 该段最后一行（通常承载韵脚）
- 或该行尾字韵母属于开放韵（a/ang/ai/ao/ou）且声调为平声（1/2/0/5）

---

## 调用预算（Call Budget）

| 阶段 | 调用次数 | 用途 | 模型参数 |
|------|---------|------|----------|
| Call #1 | 1 | 主生成（3 variants） | 默认 temp |
| Call #2 | 1 | 段级重生 revise | 默认 temp |
| Call #3 | 0~1 | 异构审校（仅 R18/R19） | temp=0.2 |
| Call #4 | 0~1 | 最终段级重生 | 默认 temp |
| **总计** | **2~4** | — | — |

**硬性封顶**：llm_calls ≤ 4。第 4 次后无论结果如何，必须 REJECTED 或输出。

---

## Trace 字段规范

每次调用必须在 trace.json 记录：

```json
{
  "call_stage": 1,
  "model_used": "claude-opus-4-1-20250805",
  "temperature": 0.2,
  "trigger_reason": "R18_R19_persist_after_call2",
  "quality_delta": {
    "before": {"craft_score": 0.72, "failed_rules": ["R18", "R19"]},
    "after": {"craft_score": 0.92, "failed_rules": []}
  }
}
```

字段说明：
- `call_stage`: 1/2/3/4
- `model_used`: 模型 ID
- `temperature`: 本次调用温度
- `trigger_reason`: 触发本次调用的原因（如 `initial_generation`, `R18_R19_persist_after_call2`, `review_found_prosody_issues`）
- `quality_delta`: 前后质量对比

---

## Fail-Loud 标准

以下情况必须 REJECTED，不输出空结果：

1. Call #1 后 HARD_KILL（R03/R14/R16_global）
2. Call #4 后仍有 R18/R19
3. 任何阶段模型返回非 JSON / schema 校验失败
4. 所有 variants 均为 dead

**REJECTED 时必须附**：
- `run_status: "REJECTED"`
- `error_stage`: 失败阶段
- `fail_reasons`: 标准化失败原因列表
- `trace`: 完整调用链证据

---

## 与 PM Rule 的映射

| PM Rule | 本决策树对应 |
|---------|-------------|
| 法则一/八：llm_calls ≤ 2 | 默认 2，R18/R19 允许 3~4，封顶 4 |
| 法则三：lint 只评分不放行草稿 | 新增 SOFT_PASS 豁免类目（R18 非韵脚 ±1） |
| 法则十一：FAIL_REASON 标准化 | 所有 REJECTED 必须附 fail_reasons |
| 法则十二：Run-ID 隔离 | 每次 E2E 用不同 out-dir，trace 独立 |

---

## 执行检查清单

- [ ] lint.py R18 弹性化实现
- [ ] main.py revise prompt 段级重生
- [ ] main.py 调用链 2→3→4
- [ ] claude_client.py 审校函数（低 temp）
- [ ] trace 字段扩展
- [ ] pytest 覆盖 R18 弹性 + 调用链
- [ ] gate-check --all 通过
- [ ] pm-audit 9/9
- [ ] docs-check 通过
- [ ] 连续 5 次 E2E 同主题 5/5 达 9/9
