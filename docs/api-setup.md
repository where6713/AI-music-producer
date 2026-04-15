# API 配置说明（你填密钥）

## 1) OpenCode 全局配置文件位置（Windows）

优先使用这个路径：

`C:\Users\admin\.config\opencode\opencode.json`

你当前机器该目录已存在（含 `opencode.json`）。

---

## 2) OpenCode 配置模板（请手动填入密钥）

> 注意：`apiKey` 只填你自己的真实密钥，不要提交到 Git。

```json
{
  "$schema": "https://opencode.ai/config.json",
  "models": {
    "gpt-5.2-codex": { "name": "gpt-5.2-codex" },
    "gpt-5.3-codex": { "name": "gpt-5.3-codex" }
  },
  "options": {
    "apiKey": "__FILL_YOUR_API_KEY__",
    "baseURL": "https://code.ppchat.vip/v1"
  },
  "provider": {
    "ppchat-codex": {
      "npm": "@ai-sdk/openai",
      "models": {
        "gpt-5.1-codex-max": { "name": "gpt-5.1-codex-max" },
        "gpt-5.2": { "name": "gpt-5.2" },
        "gpt-5.2-codex": { "name": "gpt-5.2-codex" },
        "gpt-5.3-codex": { "name": "gpt-5.3-codex" }
      },
      "options": {
        "apiKey": "__FILL_YOUR_API_KEY__",
        "baseURL": "https://code.ppchat.vip/v1"
      }
    }
  }
}
```

---

## 3) 项目内歌词 LLM 配置（lyric_architect 读取）

当前代码读取：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL` / `OPENAI_API_BASE`
- `OPENAI_MODEL`（默认 `gpt-4o-mini`）

建议在项目根目录创建 `.env`（可由 `.env.example` 复制）：

```env
OPENAI_API_KEY=__FILL_YOUR_OPENAI_API_KEY__
OPENAI_BASE_URL=https://code.ppchat.vip/v1
OPENAI_MODEL=gpt-5.3-codex
```

## 3.1) 本地模板/语料主路径（无远端素材库）

当前项目按“本地优先”运行：

- 模板：`projects/_shared/templates/modern_lostlove_v1.json`
- 语料注册表：`projects/_shared/corpus_registry.json`

在 orchestrator / lyric_architect payload 中传入：

- `structure_template_path`
- `corpus_registry_path`
- `require_real_corpus=true`

说明：项目内未使用 `CALEH_*` 配置；素材/语料走本地文件与本地注册表。

---

## 4) 最小检查步骤

1. 填好 `opencode.json` 中的 `apiKey`。
2. 在项目根目录创建 `.env` 并填入 `OPENAI_API_KEY`。
3. 运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "tools/scripts/startup_health_check.ps1"
python -m pytest tests/test_lyric_architect.py -q
```

若 `use_llm=true` 且没填密钥，系统会 fail-fast（这是预期行为，用于避免假调用）。
