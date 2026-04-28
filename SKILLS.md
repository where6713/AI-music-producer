# SKILLS — 映月工厂 · 极简歌词工坊

> **For AI agents and LLM CLIs.**
> This file defines the callable skills of this project.
> Read this file first. Then invoke the skill that matches the user's intent.
> No further context is needed to start.

---

## Environment bootstrap (run once per machine)

```bash
# 1. Install dependencies
pip install -e .

# 2. Set API key (or put in .env at project root)
export ANTHROPIC_API_KEY=sk-ant-...
```

Required: Python 3.10+, `ANTHROPIC_API_KEY`.

---

## SKILL: produce

**What it does:** Turns a raw creative intent into Suno-ready lyrics (lyrics + style + exclude tags).

**When to invoke:** User wants to write a song, generate lyrics, or describes an emotional scene/story.

**Trigger phrases (zh/en):**
- 生成 / 写歌 / 作词 / 帮我写一首 / 我想写一首关于
- generate lyrics / write a song / make lyrics for

### Command

```bash
python -m apps.cli.main produce "<raw_intent>" \
  --profile <profile> \
  --lang <lang>
```

### Parameters

| Parameter | Type | Required | Default | Notes |
|-----------|------|----------|---------|-------|
| `raw_intent` | string | yes | — | The user's creative intent. Quote it. |
| `--profile` | enum | no | `urban_introspective` | See profile table below |
| `--lang` | enum | no | `zh-CN` | `zh-CN` or `en-US` |
| `--genre` | string | no | — | e.g. `"indie pop"` |
| `--mood` | string | no | — | e.g. `"melancholic"` |
| `--vocal` | string | no | — | e.g. `"female"` |
| `--out-dir` | path | no | `out/` | Output directory |
| `--verbose` | flag | no | off | Print lint trace |

### Profile table

| `--profile` value | Display name | Use when |
|-------------------|--------------|----------|
| `urban_introspective` | 都市内省 | Late-night emotion, urban loneliness, restrained feeling **(default)** |
| `classical_restraint` | 古风留白 | Classical Chinese imagery, zen stillness, historical mood |
| `uplift_pop` | 明亮流行 | Bright pop, youthful energy, first love, courage |
| `club_dance` | 律动舞曲 | EDM, house, dance floor, release and heat |
| `ambient_meditation` | 环境冥想 | Ambient, healing, ASMR vocal, meditative calm |

**Profile inference from user's words:**

| User says | Use profile |
|-----------|-------------|
| 深夜 / 失恋 / 沉默 / 克制 / 凌晨 | `urban_introspective` |
| 古风 / 山水 / 禅 / 宫阙 / 留白 | `classical_restraint` |
| 阳光 / 初恋 / 青春 / 悸动 / 勇敢 | `uplift_pop` |
| 舞曲 / EDM / 电音 / 躁动 / club | `club_dance` |
| 冥想 / 疗愈 / 空灵 / 放松 / 呼吸 | `ambient_meditation` |

### Output

On success, these files are written to `out/` (or `--out-dir`):

| File | Content | Paste to |
|------|---------|----------|
| `out/lyrics.txt` | Section-tagged lyrics | Suno → Lyrics |
| `out/style.txt` | 4–8 GMIV style tags | Suno → Style |
| `out/exclude.txt` | Negative style tags | Suno → Exclude |
| `out/lyric_payload.json` | Full structured debug payload | — |
| `out/trace.json` | Run trace and timing | — |

### Agent behavior after invocation

1. Run the command.
2. If exit code is 0: read and display `out/lyrics.txt` in full, then one-line summary of `out/style.txt` and `out/exclude.txt`.
3. If exit code is non-zero: show last 20 lines of stderr, suggest checking `ANTHROPIC_API_KEY`.
4. Do **not** explain the pipeline. Do **not** ask for confirmation before running.

### Example invocations

```bash
# Default (urban_introspective)
python -m apps.cli.main produce "失恋三个月，深夜睡不着，想发消息又忍住了" --profile urban_introspective --lang zh-CN

# Bright pop
python -m apps.cli.main produce "第一次见面时的紧张和心跳" --profile uplift_pop --lang zh-CN

# Classical
python -m apps.cli.main produce "山中听雨，一人独坐，想起旧人" --profile classical_restraint --lang zh-CN

# English
python -m apps.cli.main produce "driving alone at 2am thinking about what went wrong" --profile urban_introspective --lang en-US
```

---

## SKILL: pm-audit

**What it does:** Runs 8 business quality checks on the last generated output. Reports PASS/FAIL per check.

**When to invoke:** User asks "check quality", "audit", "did it pass", or after a `produce` run when verbose output is needed.

**Trigger phrases:** 检查 / 审计 / 质检 / audit / check quality / did it pass

### Command

```bash
python -m apps.cli.main pm-audit
```

### Output

A table with 8 checks. Exit code 0 = all 8 passed.

| Check key | What it verifies |
|-----------|----------------|
| `chosen_variant_not_dead` | Chosen lyric variant is not killed by hard rules |
| `craft_score_floor` | craft_score ≥ 0.85 (format compliance gate) |
| `r14_r16_global_hits` | No globally forbidden cliché phrases in output |
| `few_shot_no_numeric_ids` | Few-shot examples use semantic IDs, not raw numbers |
| `audit_sections_complete` | All required sections present in payload |
| `lyrics_no_residuals` | Last lyric line is not a dangling fragment |
| `postprocess_symbols_absent` | No post-processing artifacts in output |
| `profile_source_recorded` | Profile selection is recorded in trace |

---

## SKILL: self-check

**What it does:** Verifies the system's own gate logic is consistent with production rules.

**When to invoke:** After modifying `src/lint.py`, `src/profiles/registry.json`, or gate rules. Or when user says "self-check" / "系统自检".

### Command

```bash
python -m apps.cli.main self-check
```

---

## Notes for agents

- **Do not ask the user which profile to use** unless they explicitly give no intent description at all. Infer from the table above.
- **Do not explain what you are doing** before running. Run first, show output, then offer brief notes only if something failed.
- **Output directory is always `out/`** unless the user specifies `--out-dir`.
- **Re-run = regenerate**: if the user says "重新生成" or "redo" or "try again", just re-run the same `produce` command. The system handles one automatic targeted-revise pass internally.
- **Do not modify any source files** unless the user explicitly says "fix", "修复", or "改代码".
