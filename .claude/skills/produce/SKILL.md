---
name: produce
description: Generate Suno-ready lyrics from a raw intent. Usage: /produce [意图] [#风格标签]
user-invocable: true
---

# Produce Skill

## What this skill does

Runs the full lyric generation pipeline and displays the output.

## Invocation

The user calls this skill as:

```
/produce [意图文本] [optional #风格tag]
```

Examples:
- `/produce 失恋三个月，深夜睡不着`
- `/produce 第一次见面的紧张 #流行`
- `/produce 山间的晨雾和沉默 #古风`

## Execution Steps

1. Parse the user's input after `/produce`:
   - Everything before a `#tag` is the `raw_intent`
   - The `#tag` maps to a `--profile` value (see table below)

2. Map `#tag` → `--profile`:

   | 用户写的 tag | --profile 参数 |
   |------------|--------------|
   | `#都市` `#内省` `#深夜` (or no tag) | `urban_introspective` |
   | `#古风` `#古典` `#留白` | `classical_restraint` |
   | `#流行` `#阳光` `#青春` | `uplift_pop` |
   | `#舞曲` `#EDM` `#电音` | `club_dance` |
   | `#冥想` `#空灵` `#疗愈` | `ambient_meditation` |

3. Run the CLI command:
   ```bash
   python -m apps.cli.main produce "[raw_intent]" --profile [profile] --lang zh-CN
   ```

4. After the command completes, display:
   - The full content of `out/lyrics.txt`
   - One line summary: `Style: [contents of out/style.txt]`
   - One line summary: `Exclude: [contents of out/exclude.txt]`

5. If the command exits with an error, show the last 20 lines of stderr and suggest checking `ANTHROPIC_API_KEY`.

## Do NOT

- Do not ask the user to confirm before running
- Do not show intermediate debug output
- Do not explain the pipeline unless the user asks
