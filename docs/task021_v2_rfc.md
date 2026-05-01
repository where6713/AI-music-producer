# TASK-021 V2 RFC (Revised)

## Section A · 砍除清单（精确版）

### A1. 删除（代码层）
- 删除 `src/profile_router.py` 全部（V1 路由枚举层）。
- 删除 `src/retriever.py` 中以下能力：
  - audio-feature voting
  - profile_tag voting
  - hint_scoring_disjoint_v2 相关调用
- 删除 `src/lint.py` 中 R01-R19 主体，仅保留段落格式合规 5 条 hard check。
- 删除 `src/producer_tools/self_check/gate_g7.py` 中 craft_score / quality_floor / hard_reject 计算。
- 删除 `src/profiles/registry.json`（整文件）。
- 删除 `src/profiles/global_rules.json`（整文件）。
- 删除 `src/profiles/fragments/urban_introspective.md`。
- 删除 `src/profiles/fragments/classical_restraint.md`。
- 删除 `src/profiles/fragments/uplift_pop.md`。
- 删除 `src/profiles/fragments/club_dance.md`。
- 删除 `src/profiles/fragments/ambient_meditation.md`。
- 删除 `src/profiles/fragments/indie_groove.md`。
- 删除 `src/profiles/__init__.py`（若存在）。

### A2. 删除（数据层）
- 删除 `corpus/_knowledge/suno_style_vocab.json`、`corpus/_knowledge/minimax_style_vocab.json` 中用于 hint 关键字 -> profile 分类的逻辑用途。
- 删除全部依赖 `profile_tag` 做硬路由的代码引用（以 grep 清单为准逐项消除）。

### A3. 保留（数据资产）
- 保留 `corpus/_clean/` 全部文件，不做删改。
- 保留 `corpus/{urban_introspective, classical_restraint, uplift_pop, club_dance, ambient_meditation, indie_groove}/` 下 `.txt/.json` 歌词资产，不做删改。
- 保留元数据字段 `author/title/content/emotion_tags/learn_point/do_not_copy`；`profile_tag` 字段保留为辅助元信息，但不再参与硬路由。

## Section B · 新增清单

### B1. 新增代码模块（总预算 <= 280 行 + 20 行缓冲）

单文件 hard cap（TASK-022 修订，2026-05-01）：
- `src/v2/perceive_music.py`（<=70 行，1 LLM call）
  - 输入：ref_audio + user intent
  - 输出：`music_portrait`
- `src/v2/distill_emotion.py`（<=50 行，1 LLM call）
  - 输入：intent + portrait
  - 输出：`central_image` / `arc` / `metaphor`
- `src/v2/select_corpus.py`（<=40 行，不调 LLM）
  - 输入：`corpus_index.json` + portrait
  - 输出：向 Step 3 组装 index 视图（让 Step 3 LLM 自选 ID）
- `src/v2/compose.py`（<=60 行，2 LLM calls — 2-pass 同会话）
  - 输入：portrait + emotion + golden_dozen 全文 + LLM 自选 corpus 全文
  - 输出：lyrics/style/exclude 草稿
- `src/v2/main.py`（<=30 行）
  - 编排 V2 CLI 流程（支持 `--legacy` 切回 V1）。
- `src/v2/self_review.py`（<=30 行，1 LLM call）
  - 输入：compose 初稿
  - 输出：仅做表达修缮，不改变段落结构骨架。

> 预算约束（收紧版）：
> - 各文件 hard cap：perceive_music<=70 / distill_emotion<=50 / select_corpus<=40 / compose<=60 / main<=30 / self_review<=30
> - 合计 hard cap = 280 行。预留 20 行 buffer（import/type hint/docstring/error handling）。
> - **总计控制在 <=300 行，不允许自行抬高任何单文件 cap。**
> - 若预计超 300 行，必须在 TASK-022 开工前先提报评审。

### B2. 新增工具脚本
- `scripts/build_corpus_index.py`（<=50 行）
  - 扫描 `corpus/_clean/` + `corpus/{各 profile}/` + `corpus/golden_dozen/`
  - 生成 `corpus/_index.json`（id/title/author/first_line/summary_50chars/emotion_tags/char_count）
  - 仅离线执行，不放入 runtime pipeline。

### B3. 新增数据策展
- 新建 `corpus/golden_dozen/`
- 收录 12 首人工策展文本：`<artist>_<title>.txt`
- 每首附最小 metadata 注释（来源、风格谱系、语言肌理标签）。

## Section C · LLM 自选 corpus 工作流（2-pass）

### C0. 召回降级（防 context 爆炸）
- `corpus/_index.json` 不允许全量直接塞入 Step 3 prompt。
- 必须先降到 <=120 条再进 LLM 自选池。实现二选一：
  - **方案 A（推荐）**：`select_corpus.py` 用 `music_portrait` 的 emotion/tempo/style 词做 semantic 粗筛，召回 top 80-120 条。
  - **方案 B（保底）**：按字数分桶（<=150 / 150-300 / >300）+ portrait 期望肌理选桶，再抽样到 100 条。
- 明确：这是 portrait 语义召回，不是 profile_tag 投票，不回退旧抽屉路由。

### C1. 运行时流程
1. Step 1 (`perceive_music`) 产出 `music_portrait`。
2. Step 2 (`distill_emotion`) 产出 `central_image/arc/metaphor`。
3. Step 3-pass1 (`compose`同会话前半段)：
   - 喂入 portrait + emotional core + golden_dozen 全文 + corpus_index 摘要
   - LLM 仅输出 JSON array corpus IDs。
4. 系统加载 IDs 对应全文。
5. Step 3-pass2（同一会话后半段）：
   - 回填所选全文
   - LLM 输出最终歌词三件套。
6. Step 4 (`self_review`)：
   - LLM 以主编视角做一次自审修订，保留结构，不增删主段落。

### C2. Prompt 模板（伪代码）
```text
System: 你是华语顶尖作词人。

Music Portrait: {portrait}
Emotional Core: {central_image / arc / metaphor}

Golden Dozen References (必读):
{12 首全文}

Available Corpus Index (已召回到 <=120 条, 你可以从中挑 5-10 首作为额外灵感):
{corpus/_index.json 摘要 — 每首 ~50 字}

请先输出你想引用的 corpus IDs (用 JSON array),
系统会把全文回填给你, 然后你再写歌词。
```

### C3. 预算说明
- 2-pass 在同一 Step 3 会话里完成，不增加额外独立步骤预算。

## Section D · GOLDEN_DOZEN 候选 12 首（谱系覆盖）

> 规则：优先从 `corpus/_clean/` 现有可定位文本挑选；若缺失，再外补。

1. HYBS - Dancing with my phone（indie pop 慵懒）
   - 语言肌理：轻口语、低叙事密度、节拍主导。
2. 告五人 - 爱人错过（indie pop 慵懒）
   - 语言肌理：短句循环 + 情绪反拍。
3. deca joins - 海浪（indie/松弛）
   - 语言肌理：留白多、画面感漂移。
4. 陈奕迅/林夕 - K歌之王（国语版，慢板抒情）
   - 语言肌理：密集内心独白与修辞递进。
5. 田馥甄 - 小幸运（慢板抒情）
   - 语言肌理：朴素叙事 + 情绪收束。
6. 周杰伦/方文山 - 青花瓷（古典中国风）
   - 语言肌理：古典意象串联与文白交织。
7. 五月天 - 倔强（摇滚）
   - 语言肌理：高势能动词与群唱口号感。
8. 张悬 - 宝贝（私语民谣）
   - 语言肌理：近讲亲密、低强度语义推进。
9. 周杰伦 - 晴天（流行金曲）
   - 语言肌理：青春叙事 + 旋律友好短句。
10. Khalil Fong - 三人游（R&B）
   - 语言肌理：律动切分 + 松弛韵尾。
11. 蔡依林 - 玫瑰少年（社会议题）
   - 语言肌理：议题表达与抒情平衡。
12. 林俊杰 - 修炼爱情（流行/R&B 过渡）
   - 语言肌理：情绪推进与副歌可唱性。

## Section E · 迁移路径

1. **TASK-022（V2 实现）**
   - 新建 `src/v2/` 五模块
   - 生成 `corpus_index.json`
   - 完成 `golden_dozen` 12 首策展
   - V1 以 `--legacy` 保留。
2. **TASK-023（V2 验收）**
   - 5 首伴奏 x 5 情感 prompt = 25 次 E2E
   - 架构师盲审 >=10 份“能唱起来”即通过（40% 为 V2 首版基线；进入 TASK-024 前需二次验收提高到 60%）。
3. **TASK-024（V1 砍除）**
   - 在 V2 验收通过后，按 Section A 删除 V1 路由/lint/retriever/g7 旧层。
4. **前置清理（防 hook 阻断）**
   - 在 TASK-022 开工前补齐 `docs/current_task_index.json` 占位，避免 docs-check hook 阻断提交。
5. **TASK-020 关系声明**
   - TASK-020 与 V2 正交；V2 首版 `perceive_music.py` 可先用 LLM 推理 portrait，不依赖真实 BPM/groove 提取。
   - TASK-020 完成后再切真实音频特征输入。

## Section F · Q&A（自答 6 问）

1. **不再做 profile 硬路由后，LLM 怎么知道风格？**
   - 通过 `music_portrait` 自由文本描述（BPM、律动、叙事强度、声线气质），不依赖五个抽屉枚举。

2. **保留 corpus/_clean 但不用 profile_tag，如何检索？**
   - 用 `corpus_index.json` 汇编摘要，Step 3 让 LLM 自选 IDs。

3. **LLM 会不会乱挑冲突样本？**
   - 会有风险，但 `golden_dozen` 作为必带 anchor；再通过同会话二段生成压缩偏移。

4. **没有 R01-R19 怎么防垃圾？**
   - 保留段落格式 5 条 hard + Step 4 自审 + 人耳验收；本方案把 lint 从“创作前门禁”降级为“诊断后反馈”。

5. **hint_scoring_disjoint_v2 还保留吗？**
   - 不保留。它是 profile 抽屉体系产物，关键字打分不足以表达风格上下文。

6. **未来扩新风格怎么办？**
   - 优先扩 `golden_dozen` 与 index 资产，不改路由代码；必要时仅补充 portrait 描述模板。
