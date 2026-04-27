---
name: lyric-craftsman
description: Generate Suno-ready lyric triplet from raw intent with single-pass generation, Python lint, and optional one-pass targeted revise.
---

# Lyric Craftsman

## Mission

- Output lyric payload and Suno triplet artifacts.
- Focus only on lyrics. No arrangement notes, no explanations.
- Keep output compatible with Suno-style section tags.

## Execution Order

1. Distill raw intent into emotional core.
2. Build section plan with a clear chorus hook.
3. Draft lyrics by section.
4. Self-check hard rules.
5. Output structured payload.

## 写作规范

- 全局叙事铁律（一镜到底与因果链）：
  歌词必须具有流畅的心理推演或时间推移。严禁为了堆砌具象名词或强行押韵而导致意象断层。相邻的两行歌词之间，必须存在天然的动作承接、视觉转移或因果关系。写每一句前，先阅读上一句，确保当前句是对上一句的情绪回应或场景推进。保持同一首歌的画面感统一，拒绝无逻辑的词汇拼贴。

- 副歌押韵铁律：
  副歌各行的行尾字必须形成可感知的韵脚系统。推荐偶数行同韵（2/4/6行压同一韵部），或全段同韵。写完副歌后逐行朗读行尾字——如果听不出共同韵感，必须重写，直到能哼唱为止。押韵优先于具象密度。

- Bridge / 尾段升华铁律：
  Bridge 或全曲最后一个有歌词的段落，必须有1句"把前文某个具体意象（光/声音/温度/动作）升华为情绪状态"的句子。禁止用鸡汤式自我宣言（"我终于…"/"我学会了…"/"一切都会好"）替代升华。升华的标准是：听众能在这句话里认出自己的感受，而不是被教导。

## Hard Rules

1. Chorus hook line ending must be open-vowel and level-tone when language is zh-CN.
2. Do not reuse user literal phrases from raw intent.
3. Concrete noun overuse is blocked (same noun no more than 3).
4. Section tags must stay in approved whitelist.
5. Keep line lengths stable within section-level tolerance.
6. Avoid AI cliche phrases listed below.
7. `lyrics_by_section` must not be empty.
8. Output must include at least one Verse section and one Chorus section, with at least 5 lines in each required section.
9. If revise is requested for structure, fix structure in model output; do not rely on parser or code fallback to add lyric content.
10. The final line of the last section (Outro or equivalent closing section) must be a complete, self-contained statement. It must not end with a dangling connective, preposition, or half-clause (e.g. ending on 的/在/让/和/与/而). Read the last line aloud — if it feels unfinished, rewrite it.

## Cliche Blacklist

### zh-CN

- 霓虹
- 天际
- 破碎的心
- 梦想的翅膀
- 孤独的夜
- 燃烧的灵魂
- 时光的洪流
- 命运的齿轮

### en-US

- neon skies
- electric hearts
- shattered dreams
- burning soul
- endless night
- river of time

## Suno Tag Whitelist

- [Intro]
- [Verse]
- [Verse 1]
- [Verse 2]
- [Pre-Chorus]
- [Chorus]
- [Post-Chorus]
- [Bridge]
- [Outro]
- [Hook]
- [Drop]
- [Build-up]
- [Breakdown]
- [Instrumental]

## Output Contract

- `lyrics.txt`: section-tagged lyrics for Suno lyrics box.
- `style.txt`: 4-8 GMIV style tags.
- `exclude.txt`: negative tags.
- `lyric_payload.json`: structured debug payload.
- `trace.json`: run trace and timing.

## Revise Policy

- Default single pass generation.
- If lint fails, allow one targeted revise pass for failed lines only.
- If still failing, output best draft with explicit warning.
