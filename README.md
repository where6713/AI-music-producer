# AI-music-producer

映月工厂极简歌词工坊：一个 CLI 命令 + 一份 SKILL + 单次 Claude 调用 + 动态少样本示例注入 + Python lint，产出 Suno 可粘贴三件套。

## Single Source of Truth

- 产品规范：`docs/映月工厂_极简歌词工坊_PRD.json`
- 工程法则：`one law.md`
- 目录规则：`目录框架规范.md`
- 文档归属：`docs/ai_doc_manifest.json`

## Quick Start

1) 安装依赖并完成基础检查：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/bootstrap.ps1" -InstallDeps
```

2) 配置环境变量（保留根目录 `.env`）：

```env
ANTHROPIC_API_KEY=...
```

3) 运行主命令（示例）：

```powershell
music-producer "失恋三个月想联系但知道不能"
```

## Output Contract

默认输出目录 `out/`：

- `out/lyrics.txt`：粘贴到 Suno Lyrics
- `out/style.txt`：粘贴到 Suno Style
- `out/exclude.txt`：负向标签
- `out/lyric_payload.json`：结构化调试产物
- `out/trace.json`：调用与耗时追踪

## Red Lines

- 不做 Wide Sampling（N=12）
- 不做 LLM-as-Judge 评分
- 不引入 Motif/DMR/SVO 中间件
- 不做 Web UI（CLI-only）
- 不引入向量数据库与 embedding 模型
- Few-Shot 示例数严格 <= 3

## Health Check

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/startup_health_check.ps1"
```
