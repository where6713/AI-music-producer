# 映月工厂 · 超级制片人系统 技术 PRD v1.1

> **Codename**: `music-producer`
> **形态**: Windows 11 原生 CLI · 单一 Agent 人格 · 6 个业务工具 + 2 个 Agent 自检工具
> **核心 IP**: 声音摩擦度引擎 + 中文填词物理学拦截器
> **状态**: 完整版实施规范 — 开发 Agent 拿到此文档即可直接产出可交付产品
> **相对 v1.0 的净增量**: 填词架构师、Git 卫生规则、ReAct 规划契约、Agent 调试探针、终端内播放、抽卡自动导入、动态 de-essing、语料库换血

---

## 0. 一句话定义

**这不是另一个 AI 音乐生成器。** 这是一个回答"你这把嗓子到底适合唱什么、不适合唱什么、要付出什么代价才能唱好"的命令行制片人——它替你做声学侦察、风格解构、冲突诊断、中文发音物理学拦截，把抽卡命中率从 5% 拉到 30%+，再把抽卡回来的 AI 音频"洗"成发行级母带。

用户体验参照 Claude Code：一个终端，一段对话，Agent 自主思考、提出计划、执行、自修复、交付。

---

## 1. 设计哲学：四条红线

1. **绝不造轮子**。GitHub 上有验证过的工具就用现成的。价值在工程整合与产品判断，不在算法原创。
2. **绝不浪费用户的抽卡积分**。Suno/MiniMax 每次生成都是真金白银。系统的全部计算服务于一个目标：按下"生成"之前，大概率已经知道这次会成。
3. **绝不让用户看到 traceback**。所有异常由 Agent 捕获、诊断、修复；用户只看到结果或"是否同意修复"的提问。
4. **绝不过度工程**。每增加一个模块/依赖/概念，都要能回答"砍掉它会死吗"。答案是"不会"的一律砍掉。

---

## 2. 技术栈：每一行都是 GitHub 现成方案

| 层级 | 工具 | 仓库 / 包 | 选择理由 |
|---|---|---|---|
| **Agent 大脑** | OpenAI API（已配置 OpenCode） | 官方 SDK | 零配置，工具调用 + 结构化输出原生支持 |
| **人声/伴奏分离** | Demucs v4 (`htdemucs_ft`) | `facebookresearch/demucs` | MUSDB HQ SDR 9.0–9.20 dB，业界开源 SOTA |
| **MIR 分析** | librosa | `librosa/librosa` | BPM/调性/色度/MFCC/节拍跟踪/结构分割事实标准 |
| **声纹分析** | Parselmouth | `YannickJadoul/Parselmouth` | 直调 Praat C/C++ 内核；基频/共振峰/HNR/jitter/shimmer |
| **零样本音色嵌入** | LAION CLAP (`larger_clap_music`) | HuggingFace `transformers` 接入 | **走 `transformers` 而非 `laion_clap`**，绕开依赖地狱；4M 音乐样本预训练 |
| **乐理符号分析** | music21 | `cuthbertLab/music21` | 和声/对位/调性合规检查权威库 |
| **中文拼音/声调** | pypinyin | `mozillazg/python-pinyin` | 拿声调和韵母的唯一正确方式 |
| **中文分词/词性** | jieba | `fxsjy/jieba` | 找句子的重音落点（名词/动词骨架） |
| **音频效果链** | Spotify Pedalboard | `spotify/pedalboard` | C++/JUCE 内核，比 pySoX 快 300×，Windows wheel 现成 |
| **母带匹配** | Matchering 2.0.6 | `sergree/matchering` (GPLv3) | 自带 4 位错误码体系，直接做自愈知识库种子 |
| **终端播放** | sounddevice | `spatialaudio/python-sounddevice` | 轻量，不拉整个 PyAudio 全家桶 |
| **文件监听** | watchdog | `gorakhargosh/watchdog` | Downloads 文件夹自动导入抽卡 |
| **CLI 框架** | Typer + Rich | `tiangolo/typer`, `Textualize/rich` | 优雅 CLI + 流式富文本 |
| **状态管理** | Git + SQLite | 系统自带 + `gitpython` | 配置/Prompts 归 git，音频归文件系统 |

### 2.1 语料库（换血版）

| 用途 | 资源 | 仓库 / 出处 | 备注 |
|---|---|---|---|
| **中文流行歌词 Few-Shot / 结构模板** | Chinese-Lyric-Corpus | `gaussic/Chinese-Lyric-Corpus` | 10 万+首中文流行歌词，按歌手分类；用于提取叙事骨架与字数栅格 |
| **Genre 描述词金矿** | Google MusicCaps | HuggingFace `google/MusicCaps` | 5.5k 专家标注 caption，丰富 Genre Seed 文本描述 |
| **MIDI 结构参考** | Lakh MIDI Dataset | `craffel/lmd` | 17.6 万首，用于 music21 结构分析 |
| **烂梗黑名单** | 自建 `cliche_blacklist.json` | 内置出厂 | 从 Chinese-Lyric-Corpus 做词频 + 人工拉黑初始版本 |

**显式废弃**：`chinese-poetry` 的唐诗宋词（v1.0 的错误决策，流行乐不用）。

### 2.2 显式拒绝清单

- ❌ 自训模型 / 自建标注数据集
- ❌ WebUI / GUI / Electron / Tauri / Textual 全屏 TUI
- ❌ 调 Suno/MiniMax 生成 API（用户手动抽卡）
- ❌ 本地 LLM（用 OpenAI API）
- ❌ 多 Agent 编排（一个人格，工具即服务）
- ❌ `guidance` / `outlines` 强制结构输出框架（OpenAI 原生 JSON mode 已够用）
- ❌ Podman / WSL2（Windows 原生 wheel）
- ❌ DAMP / FMA 数据集（范围蔓延，母带参考让用户自己指定）
- ❌ 区块链版权存证 / 商业模式设计（不是 PRD 该回答的问题）

---

## 3. 系统架构

### 3.1 总览

```
┌─────────────────────────────────────────────────────────────┐
│                          用户                               │
│                 (CLI 自然语言对话流)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              超级制片人 Agent (单一人格)                    │
│    OpenAI GPT + ReAct 规划 + 自愈协议 + 异常拦截            │
│                                                             │
│  行为契约:                                                  │
│  ▸ 意图解析  ▸ 提出 Plan  ▸ 用户确认  ▸ 执行                │
│  ▸ 翻译结果  ▸ 异常捕获  ▸ 自主诊断  ▸ 修复重试             │
└─┬────┬────┬────┬────┬────┬─────┬─────┬─────────────────────┘
  │    │    │    │    │    │     │     │
  ▼    ▼    ▼    ▼    ▼    ▼     ▼     ▼
┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐┌─────┐┌──────┐
│声学││风格││摩擦││填词││Pmt ││后期││shell││py    │
│分析││解构││度  ││架构││工程││精修││probe││eval  │
│师  ││师  ││计算││师★ ││师  ││师  ││     ││      │
│    ││    ││师★ ││    ││    ││    ││Agent││Agent │
│    ││    ││    ││    ││    ││    ││自检 ││自检  │
└────┘└────┘└────┘└────┘└────┘└────┘└─────┘└──────┘
  业务工具 (6)                     自检工具 (2)
  │    │    │    │    │    │
  └────┴────┴────┴────┴────┘
              │
              ▼
  ┌─────────────────────────┐
  │  项目文件系统            │
  │  ▸ Git: JSON/prompts/md  │
  │  ▸ FS:  音频/stems/takes │
  │  ▸ SQLite: 记忆 + 知识库 │
  └─────────────────────────┘
```

### 3.2 为什么是"1 Agent + 6 业务工具 + 2 自检工具"



**9 视角 = Agent 系统提示词里的 9 章知识 + 业务工具的设计依据**。

- 6 个业务工具是纯函数：输入 JSON → 输出 JSON → 无对话。
- 2 个自检工具 (`shell_probe` / `py_eval`) 只给 Agent 用，用户无权直接调用，用于未知错误的诊断与一次性脚本验证。

---

## 4. Agent 行为契约 (ReAct 规划模式)

这一节写在 Agent 的系统提示词里，是整个产品的灵魂。开发时直接塞进 `system_prompt.md` 交给 OpenAI。

### 4.1 核心原则

1. **不走死板状态机** 用户可以任意顺序喂料，Agent 自己推理出还缺什么。
2. **先规划再执行**。任何需要多步骤或耗时超过 10 秒的动作，Agent 必须先给出 Plan 让用户确认：

   ```
   [制片人] 我打算这样做:
     1. 用 Demucs 从你这段 3:42 的参考曲里分离人声
        (约 40 秒, GPU 可用)
     2. 用 librosa 提取 BPM/调性/结构
     3. 跑摩擦度计算, 和你昨天存的声纹对比
     4. 生成 Suno Prompt
   要开始吗? (y / n / 改计划)
   ```
3. **允许中途打断**。用户输入 Ctrl+C 不是崩溃，是"我改主意了"。Agent 捕获中断、保存当前状态、回到对话。
4. **主动补全上下文**。用户说"用昨天录的那段声音"，Agent 应该自己查 `voice_assets/` 目录和 SQLite 记忆去找，而不是直接报错。
5. **结论优先讲人话**。JSON 落盘留证，嘴里说的是制片人语言：
   - ❌ "基频中位数 185Hz，舒适音区 MIDI 50-64，Jitter 1.42%"
   - ✅ "你的嗓子舒适区是 D3 到 E4，再往上就紧了。偏抒情，不适合嘶吼。"
6. **主动提醒垃圾回收**。当一个项目的 `takes/` 超过 10 个废弃片段或总音频超过 2GB 时：
   > "目前 takes/ 有 15 个废片占 2.1GB。除了你标记'喜欢'的 take_003 和 take_007，其他要清掉吗?"

### 4.2 何时提 Plan、何时直接干

| 动作 | 直接执行 | 先提 Plan |
|---|---|---|
| 回答概念性问题 | ✓ | |
| 看当前项目状态 | ✓ | |
| 读/写 JSON 配置 | ✓ | |
| 播放一段音频 | ✓ | |
| 调用单个工具（<10秒） | ✓ | |
| 触发 Demucs 分离 | | ✓ |
| 触发 Matchering 母带 | | ✓ |
| 批量处理多个 take | | ✓ |
| 安装新依赖 | | ✓（需用户明确同意）|
| 清理文件 | | ✓（永远需要确认）|

---

## 5. 六个业务工具（接口规范）

### 5.1 工具一：`acoustic_analyst` 声学分析师

**职责**：克隆音/干声样本 → 声纹档案。

**实现**：若输入非纯人声，先 Demucs `htdemucs_ft` 提取；然后 Parselmouth 提基频/共振峰/HNR/jitter/shimmer/强度包络；librosa 提 MFCC；CLAP 编 512 维嵌入。

**输出 `voice_profile.json`**（同 v1.0）：包含 `f0` (median/p10/p90/comfort_range/absolute_high)、`formants` (f1/f2/f3 + vowel_space_area + brightness)、`timbre` (hnr/jitter/shimmer/breathiness/roughness)、`dynamics` (intensity_range/phrase_length)、`embedding_clap`。

---

### 5.2 工具二：`style_deconstructor` 风格解构师

**职责**：参考曲 → 音乐 DNA。

**实现**：Demucs `htdemucs_6s` 分 6 轨 (vocals/drums/bass/guitar/piano/other)；librosa 估 BPM/调性/结构；提各轨能量曲线；CLAP 整曲编码；人声轨单独跑 Parselmouth 拿原唱声纹（供摩擦度对照）。

**输出 `reference_dna.json`**（同 v1.0）：`tempo` / `key` / `structure` (分段时间戳) / `instrumentation` (各轨 presence + role) / `energy_curve` / `vocal_pitch_range_midi` / `vocal_melismatic_density` / `embedding_clap` / `stems_dir`。

---

### 5.3 工具三：`friction_calculator` 摩擦度计算师 ★

**职责**：声纹 + 参考 DNA + 用户意图 → 可操作的调和方案。

**三层瀑布**（同 v1.0，简述）：

1. **硬约束**：音域可达性、基频中心八度差、气息可持续性、花腔适配
2. **音色适配度**：CLAP 嵌入余弦相似度 → 0-100 分
3. **文化-情感对齐**：LLM 仅做翻译，不做决策

**输出 `friction_report.json`**：`overall_friction_index` / `verdict` / `conflicts[]` / `recommended_adjustments` (transpose_semitones, target_key, tempo_bpm, vocal_style_tags, instrumentation_emphasis/deemphasis, structure_modifications) / `cultural_notes`。

---

### 5.4 工具四：`lyric_architect` 填词架构师 ★ **(v1.1 新增核心 IP)**

**职责**：用户意图 → 98 分中文歌词。不是"让 LLM 自由发挥"，而是"用声学物理法则和修辞黑名单把 LLM 的输出夹逼到可用区间"。

**设计背景**：AI 写中文词的三大硬伤：
1. **高音憋死**：副歌最高音填了"哭/你/一"（闭口音），物理上唱不开
2. **倒字**：旋律下行配去声→平声，听感怪异
3. **AI 味烂梗**："星辰大海"、"孤独灵魂"、"追寻梦想"、"时光沙漏"

传统做法是反复 retry 大模型，既贵又不稳。正确做法是**流水线式拦截**。

#### 5.4.1 输入

```json
{
  "intent": "用我的嗓子唱一首失恋 R&B,碎碎念风格",
  "friction_report_path": "./friction_report.json",
  "reference_dna_path": "./reference_dna.json",
  "structure_template": null
}
```

#### 5.4.2 内部五步流水线

```
[Step 1] 结构栅格生成 (Plot Planner)
  │ 输入: 用户意图 + reference_dna 的 structure
  │ 处理: OpenAI 结构化输出 (JSON mode) 生成叙事大纲
  │ 约束: 必须产出 {verse1, pre_chorus, chorus, verse2, bridge, final_chorus}
  │      每段指定 emotional_arc + 主题关键词 + 字数栅格
  │      字数栅格从 gaussic 同风格曲目统计
  ▼
[Step 2] 草稿生成 (Draft Writer)
  │ 基于 Step 1 大纲, 分段 (非一次性) 让 LLM 写出初稿
  │ 每段完成后把前文作为上下文继续, 避免"前言不搭后语"
  │ 同时强制 Few-Shot 注入 gaussic 语料 3 首同风格范例
  │ (周杰伦/陶喆/林俊杰等)
  ▼
[Step 3] 物理层拦截 (Vowel Openness Check)
  │ pypinyin 把每一句转成带声调的拼音
  │ 定位 reference_dna 里副歌最高音的时间位置 → 映射到对应歌词字
  │ 规则: 最高音 (MIDI > 69 或用户绝对上限附近) 必须是开口音
  │      开口音: a / ai / ao / ang / e / en / o
  │      闭口音: i / u / ü / ing / un  → 命中 = CRITICAL
  │ 违规 → 调 LLM 改写: "把 X 字换成意思相近但韵母为 a/ai/ao 的字"
  ▼
[Step 4] 声调层拦截 (Tonal Collision Check)
  │ 规则: 乐句结尾的长音字, 优先使用平声 (1/2 声)
  │      命中 3/4 声的长音 → 标记为"咬合风险"
  │ 阈值: 全曲咬合风险 > 15% → 触发 LLM 二次改写
  ▼
[Step 5] 语义层拦截 (Anti-Cliché Engine)
  │ jieba 分词 → 命中 cliche_blacklist.json 计数
  │ 阈值: 烂梗率 > 5% (每 100 字 >5 个烂梗词) → 触发重写
  │ 重写 Prompt: "用物理场景代替情感形容词, 严禁使用以下词汇: [...]"
  │ 迭代上限: 3 次。第 3 次仍超标则保留并标注, 交给用户决定
  ▼
输出 lyrics.json
```

#### 5.4.3 输出 `lyrics.json`

```json
{
  "meta": {
    "intent": "失恋 R&B 碎碎念",
    "structure_ref": "周杰伦《晴天》字数栅格",
    "iterations": { "draft": 1, "vowel_fix": 2, "cliche_fix": 1 }
  },
  "sections": [
    {
      "tag": "Verse 1",
      "lines": [
        {
          "text": "便利店玻璃映着我没换的衬衫",
          "pinyin": "biàn lì diàn bō li yìng zhe wǒ méi huàn de chèn shān",
          "final_vowel": "an",
          "openness": "open",
          "tone_pattern": "4-4-4-1-4-5-3-2-4-5-4-1",
          "cliche_hits": []
        }
      ]
    }
  ],
  "warnings": [
    {
      "line_index": 14,
      "type": "tone_collision",
      "severity": "medium",
      "human": "副歌最后一句'走'(3声)落在长音上,咬合略涩。接受或让我再改?"
    }
  ],
  "stats": {
    "vowel_openness_at_peak": "pass",
    "cliche_density_pct": 1.8,
    "tone_collision_pct": 6.2
  }
}
```

#### 5.4.4 给用户的翻译版

```
[制片人] 草稿出来了,但我的填词架构师拦了两个雷:

  ① 副歌最高音原本落在'哭'字(闭口音 u),你上去会憋住。
     已改成'放开'(开口音 ai),同样是情绪爆点但能唱开。
  
  ② 草稿第二段出现了"孤独的黑夜"、"星辰大海"两个烂梗。
     已重写成具象场景:
        "霓虹把斑马线烫出裂纹"
        "旧衬衫塞进洗衣机 转得和心跳一样慢"

总共改了 3 版,最终烂梗率 1.8%,唱感通过。看一眼?
```

---

### 5.5 工具五：`prompt_compiler` Prompt 工程师

**职责**：摩擦度报告 + Genre Seed + `lyrics.json` → Suno/MiniMax 可粘贴 Prompt。

#### Suno 5.x Prompt 结构（基于公开文档与社区验证）

Suno 有三个槽：
1. **Style 字段**（无方括号）— 风格/BPM/调/人声类型/乐器
2. **Lyrics 字段** — 歌词正文 + `[Verse]/[Chorus]` 结构标签 + `[Mood:]/[Energy:]/[Instrument:]` 描述符
3. **Exclude Styles 字段** — 负面 Prompt（Suno 原生支持）

#### 编译规则

```
[Style 字段]
{genre_seed.descriptors}, {target_key}, {tempo_bpm} BPM,
{vocal_style_tags 拼接}, {instrumentation_emphasis 拼接}

[Lyrics 字段]
[Mood: {mood}] [Energy: {energy_curve_start}]
[Instrument: {top_3_instruments}]

[Intro]
[Verse 1] [intimate, moody]
便利店玻璃映着我没换的衬衫
...

[Pre-Chorus] [build-up]
...

[Chorus] [explosive release]
...

[Bridge] [tonal shift, distant reverb]
...

[Final Chorus] [biggest version]
...

[Outro] [fade]

[Exclude Styles]
{instrumentation_deemphasis} + [metal, screamo, autotune heavy,
distorted vocal, 8-bit, chiptune]
```

#### v1.1 关键升级:呼吸感前置到 Prompt 层

v1.0 原方案是后期从用户样本里采样真实吸气声物理拼接——**已废弃**。问题：底噪、空间反射、音色质感三者很难与 AI 主体人声无缝缝合，听起来假。

**新方案**：利用 Suno/MiniMax 的生成特性，在歌词文本里插入模型原生理解的呼吸标签：

```
[Verse 1] [intimate, moody]
便利店玻璃映着我没换的衬衫 [inhale]
冰柜嗡嗡响比心跳还慢 [breath]

[Pre-Chorus] [building]
我数了多少步 [soft inhale] 才走到你门口
```

这样人声是在同一潜空间内原生渲染气息，无缝度 >> 物理拼接。

#### 难咬字节拍干预

`lyric_architect` 标记的"咬合风险"字眼，在编译时自动在字后插入 `~` 或 `()`：

```
  原词: 转身就走   (走字在长音位置, 是 3 声)
  编译: 转身就~走  (让 Suno 把"走"字拉长, 改变节拍)
```

#### 输出

```
./projects/<n>/prompts/
  ├── suno_v1.txt          # 直接粘贴到 Suno Custom Mode 的格式
  ├── suno_v1_style.txt    # 只包含 Style 字段 (用户分开填时)
  ├── suno_v1_exclude.txt  # Exclude Styles 字段
  ├── minimax_v1.txt
  └── compile_log.json     # 记录每个字段的来源:哪条规则/哪个 seed
```

**自动剪贴板**：编译完主动把 Suno 的三个字段（Style / Lyrics / Exclude Styles）分别写进剪贴板历史，并告诉用户："已复制到剪贴板。打开 Suno Custom Mode，依次 Ctrl+V 到三个槽位。抽 4 张，回来我帮你筛。"

---

### 5.6 工具六：`post_processor` 后期精修师

**职责**：抽卡回来的 MP3 → 发行级母带。

#### 信号处理流程（v1.1 修正版）

```
take_001.mp3
   │
   ▼
[1] Demucs htdemucs_ft 分离
   ├─→ vocals.wav  drums.wav  bass.wav  other.wav
   │
   ▼
[2] 人声去 AI 化 (v1.1 修正)
   ├─ 共振峰扰动: ±15 cents 随机微抖 (Parselmouth Manipulation)
   │
   ├─ ★ v1.1 修正: 动态 de-essing 替代静态 6-10kHz 衰减
   │
   │   原方案: 静态 -3dB 削 6-10kHz
   │   副作用: 正常段落人声变闷
   │
   │   新方案: Pedalboard Sidechain 设计 ──
   │     board = Pedalboard([
   │       HighpassFilter(cutoff_hz=6000),    # 取 6-10k 侧链
   │       Compressor(threshold_db=-24,        # 仅在该频段能量飙升时触发
   │                  ratio=4,
   │                  attack_ms=1,
   │                  release_ms=50)
   │     ])
   │   效果: 只在咝声/AI 金属伪影出现的瞬间压
   │        保留正常段落的空气感
   │
   └─ 轻微饱和 (Distortion drive_db=2) 加暖度
   │
   ▼
[3] 对齐 (librosa onset_detect + time_stretch 局部对齐)
   │
   ▼
[4] 人声混音总线 (Pedalboard)
   Pedalboard([
     NoiseGate(threshold_db=-40),
     Compressor(threshold_db=-18, ratio=3.5,
                attack_ms=5, release_ms=80),
     LowShelfFilter(cutoff_hz=120, gain_db=-2),
     HighShelfFilter(cutoff_hz=8000, gain_db=+1.5),
     Reverb(room_size=0.18, damping=0.6, wet_level=0.12),
     Limiter(threshold_db=-1.0)
   ])
   │
   ▼
[5] 总线合并: final = vocals_fx + 0.85 * (drums + bass + other)
   │
   ▼
[6] Matchering 2.0 母带
   → master_24bit.wav (44.1kHz / 24bit)
   → master_streaming.mp3 (320kbps)
   → processing_log.json
```

**v1.1 删除**：v1.0 里的"从用户样本采样真实吸气声并叠加"步骤——理由见 5.5 节，已前置到 Prompt 层。

---

## 6. 自愈协议 v1.1：从"查字典"升级为"会 Debug"

### 6.1 两级策略

**Level 1 · 已知错误（查字典）**

出厂预填 `knowledge_base/error_solutions.sqlite`：

| 错误特征 | 自动修复 |
|---|---|
| `ModuleNotFoundError: demucs` | `pip install demucs`（询问后） |
| `CUDA out of memory` (Demucs) | fallback `--segment 7` 切片 or CPU |
| `ffmpeg not found` | 引导下载 + 写 PATH |
| Matchering `2003 ERROR` (target==reference) | 提示用户换参考文件 |
| Matchering `1001 INFO` (mono) | 自动转 stereo 重试 |
| Matchering `1002 INFO` (clipping) | 提示用户用未限幅版本 |
| Parselmouth `Sound too short` | 自动 padding 或要求重录 |
| `librosa LibsndfileError` | ffmpeg 转码后重试 |
| `OpenAI rate limit` | 指数退避重试 |

Matchering 的 4 位错误码体系整表导入，非常适合这种映射。

**Level 2 · 未知错误（自主 Debug）★ v1.1 新增**

命中不了字典的错误，Agent 有两个自检工具可以调用：

#### `shell_probe` (受限沙盒)

```json
{
  "tool": "shell_probe",
  "description": "只读探测命令,用于诊断。写入/安装/删除类命令被禁止",
  "allowlist_prefix": [
    "ffprobe", "ffmpeg -i", "ls", "dir", "type", "head", "tail",
    "where", "which", "python -c", "pip show", "pip list",
    "nvidia-smi", "systeminfo"
  ],
  "denylist_prefix": [
    "rm", "del", "rmdir", "format", "mkfs", "shutdown", "reboot",
    "pip install", "pip uninstall", "curl", "wget", "Invoke-WebRequest"
  ],
  "timeout_s": 30
}
```

**允许即执行**的只读命令，Agent 可以自主用来诊断。

**需要写入/安装**的命令（`pip install`、下载模型、删除文件），Agent 必须先向用户自然语言请示：

> "我发现是 `pedalboard` 版本太旧导致的。要不要我 `pip install -U pedalboard`?（需要联网约 5MB）"

#### `py_eval` (一次性脚本验证)

```json
{
  "tool": "py_eval",
  "description": "在隔离子进程中执行一段短脚本用于验证假设。无文件写权限,超时 30s",
  "sandbox": "subprocess with stdin piping, no writes outside /tmp"
}
```

### 6.2 实际场景示例

**场景**：用户 `master take_001.mp3`，Pedalboard 抛 `ValueError: sample rate mismatch`。

**Agent 内部流程**（用户看不到这些）：

```
[Thought] 未知错误,查字典无匹配。
[Action] shell_probe: "ffprobe ./projects/.../takes/take_001.mp3"
[Observation] 输出显示采样率 44100
[Action] shell_probe: "ffprobe ./masters_ref/beyond_haikuo.wav"
[Observation] 输出显示采样率 48000
[Thought] 确认是采样率冲突。需要先重采样到 44100。
[Action] py_eval: 写一段 librosa.resample 的脚本验证
[Observation] 重采样成功,输出波形正常
[Action] 修改 post_processor 管线,在 Matchering 前插入 resample 步骤,重试
[Observation] 成功
```

**用户看到的**：

```
[制片人] 处理中... (系统侦测到采样率冲突,正在自动重采样,无需干预)
[制片人] ✓ 母带完成。master_24bit.wav (3:42, -14 LUFS)
         要听一下吗? [play master]
```

### 6.3 知识库累积

每次成功修复的未知错误，自动写回 `error_solutions.sqlite`。下次遇到相同特征直接走 Level 1 字典。**Agent 会主动告诉用户**："我新学会处理 X 类错误，以后这种问题会自动修。"

---

## 7. Git 卫生规则 ★ (v1.1 关键修正)

### 7.1 v1.0 的致命 bug

v1.0 里说"每个项目是一个 git repo，每次决策触发 commit"。但**没有排除二进制音频**。结果：Demucs 分出来的 stems（几十 MB）、每个 take（几 MB）、每个 master（几十 MB），全进 git 对象库。频繁切分支会让 `.git/` 体积一周暴涨到几 GB，小白用户毫无察觉直到磁盘爆。

### 7.2 v1.1 修正

每个项目 `git init` 时自动写入 `.gitignore`：

```gitignore
# .gitignore (auto-generated)
# 二进制音频永远不进 git
*.wav
*.mp3
*.flac
*.ogg
*.aac
*.m4a

# Demucs 分离产物 / 模型缓存
stems/
takes/
masters/
*.npz
*.pt
*.safetensors

# 但这些必须跟踪
!intent.md
!voice_profile.json
!reference_dna.json
!friction_report.json
!lyrics.json
!prompts/
!compile_log.json
```

Git 只追踪：**意图、声纹档案、风格 DNA、摩擦度报告、歌词结构、Prompt 文本、编译日志**——全是小 JSON 和 Markdown，分支切换秒级完成。

### 7.3 对用户隐藏 git

小白用户不懂 git 命令。系统用**语义标签**暴露版本概念：

| 用户说 | Agent 内部做的事 | 用户感知 |
|---|---|---|
| "我想试试摇滚版" | `git checkout -b v2_rock_style` | "好,我开了个'摇滚版'分支" |
| "切回原来那版" | `git checkout main` | "回到主线了" |
| "对比这两版" | git diff + rich 表格 | 富文本并排显示关键参数 |
| "删掉摇滚版" | `git branch -D v2_rock_style` + 确认 | "已删除'摇滚版'。你标记喜欢的主线还在。" |

用户永远不需要敲 `git` 字眼。

### 7.4 音频文件的版本管理

音频不进 git，但仍需版本追踪。方案：**SQLite registry + 物理文件目录**。

项目内结构：

```
projects/2026-04-07_jay_style/
  ├── .git/                     # 只存 JSON+MD
  ├── .gitignore
  ├── intent.md                 # git tracked
  ├── voice_profile.json        # git tracked
  ├── reference_dna.json        # git tracked
  ├── friction_report.json      # git tracked
  ├── lyrics.json               # git tracked
  ├── prompts/                  # git tracked
  │   └── suno_v1.txt
  │
  ├── assets/                   # git ignored, 音频物理存储
  │   ├── reference.mp3
  │   ├── voice_sample.wav
  │   ├── stems/
  │   │   ├── vocals.wav
  │   │   └── ...
  │   ├── takes/
  │   │   ├── 20260407_153022_take01.mp3
  │   │   └── 20260407_153245_take02.mp3
  │   └── masters/
  │       └── 20260407_160105_master.wav
  │
  └── .producer_state.sqlite    # git ignored
                                 # 记录"branch -> 音频物理路径"映射
```

`.producer_state.sqlite` 表结构：

```sql
CREATE TABLE audio_registry (
  commit_hash TEXT,      -- git HEAD at the moment
  branch      TEXT,      -- semantic name (e.g. "v2_rock_style")
  kind        TEXT,      -- "reference" / "voice" / "take" / "master" / "stem"
  file_path   TEXT,      -- physical path under assets/
  created_at  TIMESTAMP,
  user_label  TEXT,      -- "喜欢" / "候选" / "废弃" / null
  notes       TEXT
);
```

切换分支时，Agent 查这张表找出该分支对应的音频物理路径。用户感觉是"切到摇滚版所有东西都在"，实际 git 只切了 JSON，音频从同一物理目录按 commit 指针索引。

---

## 8. 用户体验：打破终端的"聋"与"摩擦力"

### 8.1 终端内播放 ★ v1.1 新增

v1.0 的痛点：听 take 要切回资源管理器双击——严重割裂制片沉浸感。

v1.1 方案：`sounddevice` + `soundfile` 轻量接入。

```
> play take_001
[制片人] ♪ 播放中: take_001.mp3 (0:00 / 3:42)
         [q 停止] [空格 暂停/继续]

> play diff
[制片人] 轮流播放原版 vs 精修版:
         [1/2] 原版 take_001.mp3...
         [2/2] 精修版 master_24bit.wav...
         哪个更好? [1 / 2 / 继续]
```

用户从头到尾不离开键盘。

### 8.2 抽卡自动导入 ★ v1.1 新增

v1.0 的摩擦：Suno 抽完 → 下载 → 找到文件 → 移动到项目目录 → 命令行 import-take。小白会在"找到文件"这一步卡住。

v1.1 方案：`watchdog` 后台监听用户的 Windows 默认下载目录。

```python
# 启动时挂载监听
class DownloadWatcher(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(('.mp3', '.wav')):
            fname = os.path.basename(event.src_path)
            # Suno 导出文件通常有 suno-* 或包含 suno 字样
            if 'suno' in fname.lower() or matches_current_project_pattern(fname):
                auto_import_to_current_project(event.src_path)
                notify_agent("new_take_detected", event.src_path)
```

用户体验：

```
[用户在浏览器里点 Suno 下载按钮]

(2 秒后,制片人终端窗口主动弹消息)

[制片人] 📥 侦测到新抽卡结果: Suno_放晴那天_v1.mp3
         已归入当前项目 takes/20260407_163322_take01.mp3
         要现在听一下吗? 还是直接开始精修?
         [play / master / 等等]
```

监听开关在 `config.json` 里，可关闭（隐私顾虑）。

### 8.3 对话界面：Rich 流式输出 + 单列布局

**不做**分屏 TUI（Textual）。理由：过度工程、学习成本、小白不习惯、崩溃恢复复杂。

**做**：单列对话流 + Rich 富文本即可。技术细节用表格折叠，大白话结论用颜色和图标点缀。

```
╭─ 🎬 映月工厂 · 超级制片人 ────────────────────────────╮
│ 上次见面: 2026-04-07 23:14                            │
│ 当前项目: 2026-04-07_jay_style                        │
│ 分支: main                                            │
│ 状态: 已完成摩擦度分析,等你给参考歌词或我帮你写        │
╰────────────────────────────────────────────────────────╯

[制片人] 早上好 Candice。昨天我们卡在歌词这一步。
         你是自己来写,还是让我的填词架构师帮你搞一版?

> 你来吧,但别写那种 AI 味的

[制片人] 收到。给我 1 分钟。
         
         🎭 大纲规划 ✓
         ✍️  草稿生成 ✓  (参考: 陶喆《普通朋友》字数栅格)
         🔍 物理层扫描... 发现 2 处高音闭口音
         🔧 修正中... ✓
         🔍 声调层扫描... 通过 (咬合风险 4.2%)
         🔍 语义层扫描... 发现 1 处烂梗 "流浪的心"
         🔧 改写中... ✓
         
         ✓ 完成。3 轮迭代,烂梗率 1.8%,唱感合格。
         
         要看完整版还是只看副歌?
         [full / chorus / play 预演片段]
```

---

## 9. CLI 命令参考（自然语言优先）

用户 99% 的时间用自然语言。显式命令只给老鸟用。

| 命令 | 自然语言触发 | 动作 |
|---|---|---|
| `new <n>` | "新建项目叫 xxx" | 创建文件夹 + git init + .gitignore |
| `use-voice <file>` | "分析这段干声" / "用昨天那段声音" | acoustic_analyst |
| `analyze <ref>` | "解析这首参考曲" | style_deconstructor |
| `check-fit` | "看看配不配" | friction_calculator |
| `write-lyrics` | "帮我写词" / "按这个意思填词" | lyric_architect |
| `compile [--target]` | "编 Prompt" / "给我 Suno 用的" | prompt_compiler |
| `master <take>` | "精修这条" | post_processor |
| `play <file>` | "放一下 take_001" | sounddevice 播放 |
| `play diff <a> <b>` | "AB 对比" | 轮流播放 + 投票 |
| `branch <semantic_name>` | "试试摇滚版" | git checkout -b + registry 登记 |
| `switch <n>` | "切回主线" | git checkout |
| `compare <a> <b>` | "对比这两版" | rich 表格 diff |
| `status` | "到哪了" | 当前项目状态总览 |
| `clean` | "清理一下" | 垃圾回收向导 |

---

## 10. 数据流总览

```
用户克隆音 ──┐
            ├─→ acoustic_analyst ──→ voice_profile.json ──┐
用户参考曲 ──┴─→ style_deconstructor ─→ reference_dna.json ┤
                                                          │
                                                          ▼
                                              friction_calculator
                                                          │
                                                          ▼
                                              friction_report.json
                                                          │
                                  (用户意图 + gaussic 语料 +
                                   cliche_blacklist + MusicCaps)
                                                          │
                                                          ▼
                                              lyric_architect
                                                (5 步流水线)
                                                          │
                                                          ▼
                                                   lyrics.json
                                                          │
                                                          ▼
                                              prompt_compiler
                                                          │
                                          ┌───────────────┴───────────────┐
                                          ▼                               ▼
                                    suno_v1.txt                    minimax_v1.txt
                                          │
                              ┌───────────┘
                              │
                              ▼
                   [用户在浏览器手动抽卡]
                              │
                              ▼
                   watchdog 侦测 → 自动归档
                              │
                              ▼
                   assets/takes/take_*.mp3
                              │
                              ▼
                      post_processor
                              │
                              ▼
                assets/masters/master_*.wav
```

全程文件系统驱动，崩溃可续。Agent 重启从最后一个落盘 JSON 接着干。

---

## 10.1 扩展方案定稿（一次性写入）

本条为当前版本的正式范围裁决：**纳入 ①②③④，明确排除 ⑤**。

| 编号 | 方案 | 定稿结论 | 落点模块 | 复杂度控制约束 |
|---|---|---|---|---|
| ① | 词曲倒字（pypinyin + 同义替换） | **纳入** | `lyric_architect` + `prompt_compiler` | 仅做规则层与词替换，不引入新服务 |
| ② | 结构留白（抽轨静音 + 进场 Delay） | **纳入** | `post_processor`（编排规则） | 复用现有 Demucs 能力，**不新增 `audio-separator` 依赖** |
| ③ | 人声拼轨（DTW + Crossfade） | **纳入** | `post_processor` 内新增 `Take_Stitcher` 子流程 | 复用 `librosa` + `soundfile`，不新增模型依赖 |
| ④ | 完美缺陷（颤音延迟/共振峰微调） | **纳入** | `post_processor` 内新增 `Vocal_Naturalizer` 子流程 | 复用 `praat-parselmouth` + `pedalboard`，参数保守默认 |
| ⑤ | 客观质量评估（ViSQOL + FAD） | **排除** | - | 本版不引入新评分链路，避免模型与运维负担上升 |

补充说明：
- `Take_Stitcher` 与 `Vocal_Naturalizer` 是 `post_processor` 内部子流程命名，不增加独立运行时服务。
- 本文所有“复杂度不升高”语义，均指**不新增额外长期运维面**（新服务、新模型集群、新守护进程）。

---

## 11. 不做的事 · 最终防过度工程清单

| 想做但不做 | 不做的理由 |
|---|---|
| 实时音频流监听 | 用户手动抽卡,不需要 |
| 多 Agent 编排 | 一个人格一个声音 |
| 自训练摩擦度模型 | 规则瀑布足够 |
| 自训练填词模型 | OpenAI + 物理拦截足够 |
| 调 Suno/MiniMax 生成 API | 合规与成本 |
| WebUI / 桌面 GUI / Textual TUI | CLI 是约束 |
| Podman / Docker / WSL | Windows 原生 wheel |
| guidance / outlines 框架 | OpenAI JSON mode 够用 |
| chinese-poetry 语料 | 流行乐用错语料,已换 gaussic |
| 区块链存证 / 授权分级 | 不是 PRD 问题 |
| 遗传算法 Prompt 优化 | 抽卡太贵 |
| 全文件快照 + 回滚树 | git + registry 就够了 |
| ViSQOL + FAD 客观评分链路 | 本版明确排除，收益不匹配复杂度与运维成本 |

---

## 12. 依赖清单（完整 `requirements.txt`）

```txt
# Agent & CLI
openai>=1.30
typer>=0.12
rich>=13.7

# 音频核心
demucs>=4.0.1
librosa>=0.10.2
soundfile>=0.12
praat-parselmouth>=0.4.5

# 嵌入与语义
transformers>=4.40
torch>=2.1
accelerate>=0.30

# 效果链与母带
pedalboard>=0.9.12
matchering>=2.0.6

# 乐理
music21>=9.1

# 中文填词
pypinyin>=0.51
jieba>=0.42

# 明确不引入（本版排除）
# visqol
# frechet-audio-distance

# 终端播放 & 文件监听
sounddevice>=0.4.6
watchdog>=4.0

# 状态 & 存储
gitpython>=3.1
sqlalchemy>=2.0
```

**系统依赖**：ffmpeg（PATH）、VC++ Redist 2019+、Git for Windows。

**首次启动自动下载**（总计约 1GB，Agent 在需要时逐个请求用户同意）：
- Demucs `htdemucs_ft`（~320MB）
- LAION `larger_clap_music`（~640MB via HuggingFace cache）
- `gaussic/Chinese-Lyric-Corpus`（~80MB）
- `cliche_blacklist.json`（<1MB，出厂内置）
- `google/MusicCaps` metadata CSV（<5MB）

---

## 13. 交付标准（给开发 Agent 的验收清单）

开发完成后，以下 12 条流程必须全部跑通，且用户全程不看到任何 Python 错误：

1. **冷启动**：`music-producer` 首次运行，向导下载依赖模型，落到 `~/.music-producer/`。
2. **声纹录入**：上传 30 秒干声 → 60 秒内拿到 `voice_profile.json` 和大白话总结。
3. **参考解析**：拖一首 3 分钟 mp3 到对话框 → 120 秒内完成分轨 + DNA 提取。
4. **摩擦度**：一条命令拿到可读的冲突清单 + 调整建议。
5. **填词**：给一句意图 → 3 分钟内拿到通过物理/声调/语义三层拦截的歌词。
6. **编译**：一条命令拿到 Suno Prompt 三件套（Style/Lyrics/Exclude），自动进剪贴板。
7. **抽卡回流**：浏览器下载 Suno 结果 → 10 秒内 Agent 自动导入并通知。
8. **精修**：一条命令跑完去 AI 化 + 混音 + 母带，输出 24bit WAV。
9. **终端播放**：`play master` 直接在终端听，不开外部播放器。
10. **分支实验**："试试摇滚版" → Agent 自动 branch，重新跑摩擦度和 Prompt，可切换回主线。
11. **错误自愈**：人为制造一个采样率冲突或依赖缺失，Agent 自主诊断并修复，用户无感知。
12. **垃圾回收**：攒 10 个废片后，Agent 主动提醒并清理。

以上 12 条全部通过 = 可交付给用户。

---

## 14. 给 Candice 的话

v1.1 相对 v1.0 的本质变化是三件事：

1. **填词从"找几首唐诗"变成"声学物理学拦截"**。`lyric_architect` 是你之前没意识到但一定需要的核心 IP——中文流行乐的生死线不是"有没有辞藻"，而是"高音区填的字唱不唱得开"。这条线 pypinyin + 一份烂梗黑名单就守住了，成本极低。

2. **Agent 从"路由器"变成"会 debug 的初级程序员"**。`shell_probe` + `py_eval` 两个自检工具，让它能处理出厂没见过的错误，但又被权限白名单锁死不会乱删文件。这是 Claude Code 体验的精髓。

3. **Git 只管脑子,不管肉体**。二进制音频交给文件系统 + SQLite registry，JSON/prompts/md 交给 git。分支切换永远秒级。这个错误我在 v1.0 没看出来，架构师一针见血。

还是那句话：**这份 PRD 不是圣经，是出发点**。如果开发 Agent 在实现时发现某个工具有更合适的替代，换。但四条红线——不造轮子/不浪费抽卡/不暴露 traceback/不过度工程——别碰。

---

**END OF PRD v1.1**
