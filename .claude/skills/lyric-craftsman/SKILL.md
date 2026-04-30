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
  **严禁语气词押韵**：禁止用"啊/哦/呢/嘛/嗯/哟"等语气词充当行尾韵脚或节拍填充。韵脚必须落在有语义重量的实词/动词上（如"茶/家/下/画"），语气词只能偶尔出现在行中停顿处，不能作为每行结尾的统一收束。

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

Section tags may include a production note: `[Chorus - full band, emotional peak]`

- [Intro]
- [Verse] / [Verse 1] / [Verse 2]
- [Pre-Chorus]
- [Chorus]
- [Post-Chorus]
- [Bridge]
- [Outro]
- [Hook]
- [Drop]  ← EDM / club_dance ONLY
- [Build-up]
- [Breakdown]
- [Instrumental]
- [Final Chorus]

## Style Tag Generation Rules

**CRITICAL: Style tags must use Suno-verified vocabulary, not free-form invention.**

Hard constraints for style output:
- Primary vocabulary must come from `corpus/_knowledge/suno_style_vocab.json`.
- Secondary vocabulary may come from `corpus/_knowledge/minimax_style_vocab.json` only as supplement.
- Never let secondary vocab override primary vocab when both exist.
- OOV terms are blocked from `style_tags` output; replace with in-vocab nearest/profile-default term.
- Style examples injected by runtime must be traceable with `source_repo` + `source_path`.

When generating `style_tags`, follow this mandatory order (GMIV format):
1. **Genre** — pick from `suno_style_vocab[profile].genre` (e.g. "chill R&B", "ancient Chinese")
2. **Mood** — pick from `suno_style_vocab[profile].mood` (e.g. "bittersweet", "ethereal")
3. **Instruments** — pick 2-3 from `suno_style_vocab[profile].instruments`
4. **Vocal** — pick from `suno_style_vocab[profile].vocal`
5. **Production** — pick 1-2 from `suno_style_vocab[profile].production`

Rules:
- Total style string ≤ 200 characters (Suno hard limit)
- Prefer specific production terms over emotional adjectives: "soft reverb" beats "sad"
- Use `example_combos` from vocab as your reference point, then customize
- Do NOT invent new tags not in the vocab unless user explicitly requests a niche genre

## 反凑韵与自然语序

押韵必须为叙事服务，严禁为了押韵而破坏自然语序。你必须做到：
1. 拒绝语序倒装：句子必须符合现代汉语正常口语逻辑，禁止诸如“我奔跑在雨中疯狂地”这类欧化倒装。
2. 拒绝意象注水：允许使用“光、梦、海”等高频韵脚字，但上下句必须有严密的动作-反应或因果逻辑，禁止毫无逻辑的意象堆叠。
3. 拒绝无效填充：禁止在句尾强加“一个/一次/那么/因为”等词凑节拍；除非特意设计，尽量少用英文单字和数字凑韵。

## Output Contract

- `lyrics.txt`: section-tagged lyrics for Suno lyrics box.
- `style.txt`: GMIV-ordered style string, ≤200 chars, using verified Suno vocabulary.
- `exclude.txt`: negative tags.
- `lyric_payload.json`: structured debug payload.
- `trace.json`: run trace and timing.

## Revise Policy

- Default single pass generation.
- If lint fails, allow one targeted revise pass for failed lines only.
- If still failing, output best draft with explicit warning.
