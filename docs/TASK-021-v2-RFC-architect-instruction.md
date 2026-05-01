# 架构师终局口令 · TASK-021 修订版原文（照抄）

## 自我修正 · 我上一轮偏颇了 · 修订 TASK-021 范围

### 先认错

你说得对。**我上一轮提议"砍掉 `corpus/{5 profiles}/`"是偏颇的**，犯了一个典型的过度反应错误：把"被错误使用的资产"和"资产本身"混淆了。

`corpus/_clean/` 里已经付出过的清洗成本——GitHub 抓取（chinese-poetry / Chinese-Lyric-Corpus 等仓）+ 编码清洗 + 字段标注 + 去重——是**真金白银的工程资产**，几千条中文歌词 + 元曲 + 古诗都已经在那里。把它和"profile 路由反模式"一起扔掉是浪费摊销。

**真正的反模式不是 corpus 本身，是 `profile_tag` 字段被当作硬路由维度+`hint_scoring_disjoint_v2` 用关键字（光/天/梦/笑/走/风/飞）打分硬塞进 5 个抽屉。**

看你给的样本就知道这个分类有多粗暴：

- 「你怎么舍得我难过」明明是抒情慢板，被塞进 `uplift_pop` 仅因含"梦/天/走/风"4 个 hint 字
- 关汉卿《诈妮子调风月》整组戏曲唱词全部贴 `nostalgia/restraint/imagery` 三连 emotion_tag，但不同曲牌情感天差地别

**问题在分类层，不在文件层**。

---

## 修订后的中庸方案 · corpus 二层架构

```
┌──────────────────────────────────────────────────┐
│  Layer 1 · 全量灵感池 (保留)                       │
│  corpus/_clean/  ← 几千条已清洗资产, 一字不删       │
│  - 删除: profile_tag 作为硬路由维度的代码引用      │
│  - 保留: 文件 + 元数据字段 (author/title/content/  │
│         emotion_tags/learn_point/do_not_copy)     │
│  - 用途: Step 1 完成后, LLM 自选 5-10 条作灵感     │
└──────────────────────────────────────────────────┘
                       +
┌──────────────────────────────────────────────────┐
│  Layer 2 · GOLDEN_DOZEN 精品尺 (新增 ≤12 首)       │
│  corpus/golden_dozen/  ← 人工策展                  │
│  - 每次生成必带 (无论 music_portrait 是什么)       │
│  - 华语谱系灵魂尺度尺: HYBS/告五人/林夕/方文山/    │
│    田馥甄/陈奕迅/张悬/蔡依林/周杰伦/五月天/        │
│    Khalil Fong/deca joins                         │
│  - 用途: 给 LLM 提供"顶尖参照系", 避免在大池里被    │
│    平庸样本拉低均值                                │
└──────────────────────────────────────────────────┘
```

**比我上一版多出来的收益**：

1. 保留几千条已清洗资产，零浪费
2. 多样性保留（古诗、元曲、各类流行歌手都在）
3. GOLDEN_DOZEN 提供风格 anchor，不让 LLM 在大池里漂
4. 同时仍然达成核心目标——**断开"profile 抽屉硬路由"反模式**

---

## 检索方式 · 从"profile 投票"改"LLM 自选"

```
旧 (反模式):
  audio → bpm/groove → retriever vote → profile_tag 投票 → 
  fragment 加载 → fragment 喂给 Compose LLM
  ↑ 决定权在 hint 关键字，LLM 被关在抽屉里

新:
  Step 1: audio + user_prompt → LLM 输出 music_portrait
  Step 1.5: 系统给 LLM 看 corpus_index.json (标题/作者/首句/emotion_tags)
            + GOLDEN_DOZEN 摘要
  Step 1.6: LLM 自选 5-10 条 ID + GOLDEN_DOZEN 全部
  Step 2: 系统按 ID 加载全文进 Step 3 的 prompt context
  ↑ 决定权在 LLM 整体感
```

`corpus_index.json` ≈ 1 个文件，从 `corpus/_clean/*.json` 自动汇编（脚本一次性跑出来），不再做硬分类。

---

## 给开发 agent 的修订版 RFC 口令

> # TASK-021 修订版 · V2 极简化重构 RFC（架构师反偏颇修正）
>
> ## 上一版偏颇修正声明
>
> 上一轮口令里"砍掉 `corpus/{urban_introspective, classical_restraint, uplift_pop, club_dance, ambient_meditation, indie_groove}/`"的提法**作废**。这些目录承载的是 GitHub 已抓取已清洗的真实资产，不应丢弃。真正要打掉的是 `profile_tag` 字段作为硬路由维度的使用方式 + `hint_scoring_disjoint_v2` 的关键字打分分类法。
>
> ## 任务交付物：`docs/task021_v2_rfc.md`，必须包含 6 节
>
> ### Section A · 砍除清单（精确版）
>
> **删除（代码层）**：
>
> - `src/profile_router.py` 全部
> - `src/retriever.py` 中的 audio-feature voting / profile_tag voting / hint_scoring 调用
> - `src/lint.py` 中的 R01–R19 主体（保留段落格式合规 5 条）
> - `src/producer_tools/self_check/gate_g7.py` 中的 craft_score / quality_floor / hard_reject 计算
> - `src/profiles/` 全部 5 个 `fragment.md` 与 registry.json 中"profile 作为路由 enum"的部分
>
> **删除（数据层）**：
>
> - `corpus/_knowledge/{suno_style_vocab, minimax_style_vocab}.json` 中的"hint 关键字 → profile 分类"逻辑
> - 任何依赖 `profile_tag` 字段做硬路由的代码引用（grep 找全）
>
> **保留（数据资产）**：
>
> - ✅ `corpus/_clean/` **全部文件一字不删**
> - ✅ `corpus/{urban_introspective, classical_restraint, uplift_pop, club_dance, ambient_meditation, indie_groove}/` 中的 .txt / .json 歌词文件全部保留
> - ✅ 元数据字段 `author / title / content / emotion_tags / learn_point / do_not_copy` 全部保留（仅废弃 `profile_tag` 字段的硬路由用途，字段本身可作为辅助元信息）
>
> ### Section B · 新增清单
>
> **代码（≤300 行新增）**：
>
> - `src/v2/perceive_music.py` (≤80 行, 1 LLM call, 输出 music_portrait)
> - `src/v2/distill_emotion.py` (≤60 行, 1 LLM call, 输出 central_image/arc/metaphor)
> - `src/v2/select_corpus.py` (≤50 行, **不调 LLM**, 把 corpus_index.json 与 music_portrait 一起塞给 Step 3, 让 Step 3 LLM 自选 ID)
> - `src/v2/compose.py` (≤70 行, 1 LLM call, 接收 portrait + emotion + golden_dozen 全文 + LLM 自选 corpus 全文)
> - `src/v2/main.py` (≤40 行, CLI orchestration)
>
> **工具脚本**：
>
> - `scripts/build_corpus_index.py` (≤50 行) — 扫 `corpus/_clean/` + `corpus/{各 profile}/` + `corpus/golden_dozen/` 生成 `corpus_index.json`（包含 id / title / author / first_line / emotion_tags / 字数）。**这个脚本一次跑一次，不在 pipeline 里跑**。
>
> **数据策展**：
>
> - 新建 `corpus/golden_dozen/` 目录, 12 首人工挑选, 文件名 `<artist>_<title>.txt`（候选名单见 Section D）
>
> ### Section C · LLM 自选 corpus 的工作流
>
> 详细写出 Step 3 的 prompt 模板（伪代码）：
>
> ```
> System: 你是华语顶尖作词人。
>
> Music Portrait: {portrait}
> Emotional Core: {central_image / arc / metaphor}
>
> Golden Dozen References (必读):
> {12 首全文}
>
> Available Corpus Index (你可以从中挑 5-10 首作为额外灵感):
> {corpus_index.json 摘要 — 每首 ~50 字}
>
> 请先输出你想引用的 corpus IDs (用 JSON array), 系统会把全文回填给你, 然后你再写歌词。
> ```
>
> 这是 **2-pass interaction**: 第一 pass LLM 自选 ID, 第二 pass 系统注入全文 LLM 写词。这两次都算同一次 Step 3 (在同一个 conversation 里), 不额外消耗预算。
>
> ### Section D · GOLDEN_DOZEN 12 首候选名单
>
> 列出每首附 1 句"代表的语言肌理"。必须覆盖以下谱系（不准全塞同一种）:
>
> - indie pop 慵懒（HYBS / 告五人 / deca joins）
> - 慢板抒情（陈奕迅+林夕 / 田馥甄）
> - 古典中国风（方文山）
> - 摇滚（五月天）
> - 私语民谣（张悬）
> - 流行金曲（周杰伦）
> - R&B（Khalil Fong）
> - 社会议题（蔡依林）
>
> 12 首必须从 `corpus/_clean/` 里能找到的歌优先（zero-cost 挑选），找不到再外补。
>
> ### Section E · 迁移路径
>
> 1. **TASK-022 (V2 实现)**: 写 v2/ 5 个新文件 + corpus_index.json 生成 + golden_dozen 12 首策展。V1 留 `--legacy` 不删。
> 2. **TASK-023 (V2 验收)**: 5 首伴奏 × 5 个情感 prompt = 25 次 E2E。架构师听感盲审 ≥10 份"能唱起来"即过。
> 3. **TASK-024 (V1 砍除)**: 通过验收后删 V1 路由层 / lint / retriever / gate_g7（按 Section A）。
>
> ### Section F · Q & A（自答 6 问）
>
> 1. **不再做 profile 硬路由后, LLM 怎么知道选哪种风格?**
> → music_portrait 是自由文本, LLM 在 Step 1 已经自己判定 ("100-110 BPM 慵懒 indie pop"), 不需要 5 个枚举抽屉
>
> 2. **保留 corpus/_clean/ 但不用 profile_tag, 那这些文件怎么被检索到?**
> → corpus_index.json 一次性汇编, Step 3 LLM 自己看摘要挑 ID
>
> 3. **LLM 会不会乱挑、挑到风格冲突的样本?**
> → 会有但 GOLDEN_DOZEN 永远必带, 提供 anchor; 而且 LLM 看到 portrait 后挑相关样本是其训练强项
>
> 4. **没有 lint R01–R19 怎么保证不写垃圾?**
> → Step 4 self-edit (LLM 戴主编帽自审一次) + 段落格式 5 条 hard 保留 + 用户耳朵
>
> 5. **`hint_scoring_disjoint_v2` 那种关键字打分还要不要保留?**
> → 完全废弃, 它是 profile 抽屉的产物, 把"风/天/走"等动词当风格特征是反模式
>
> 6. **如果未来要加新风格 (比如说"日系 city pop")怎么办?**
> → 加 1 首到 GOLDEN_DOZEN, 不动一行代码
>
> ## 红线
>
> 1. ❌ 不许动 `corpus/_clean/` 任何文件（这是已付出的资产）
> 2. ❌ 不许动 5 个 profile 目录下的 .txt / .json 歌词文件（资产保留）
> 3. ❌ 不许在 RFC 里写一行业务代码（RFC 阶段）
> 4. ❌ 不许偷渡 profile / fragment / retriever 等旧概念到 v2/（用 music_portrait / corpus_index 等新名字，切割历史）
> 5. ❌ 不许给 LLM 加新硬约束规则
> 6. ✅ GOLDEN_DOZEN 必须风格分布合理, 不许 12 首都堆同一谱系
>
> ## 验收
>
> RFC 提交后架构师审 5 项:
>
> 1. Section A 删除范围是否精确（**不许误删 corpus 数据资产**）
> 2. Section B 新增模块行数是否克制（5 个文件总行数 ≤ 300）
> 3. Section C 2-pass 工作流是否清晰可实现
> 4. Section D 12 首是否真覆盖谱系且优先取自 _clean
> 5. Section F 自答是否诚实
>
> 通过即开 TASK-022 实现。

---

## 给 Candice 的元话

你这个截停救了一次。我上一轮在"破除工程化反模式"的方向上走对了，但**反应过度地把数据资产也归到反模式里**——这是经典的 baby with bathwater 失误。

修正后的方案是**双层架构**：

- **底层**保留你已付出清洗成本的所有 corpus（不浪费）
- **上层**新增 12 首精品策展（不漂移）
- **路由层**彻底打掉 profile 抽屉 + hint 关键字打分（这才是真反模式）

把上面那段修订版口令直接发给开发 agent。RFC 回来我再审，确认没把数据资产误删。
