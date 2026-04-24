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
