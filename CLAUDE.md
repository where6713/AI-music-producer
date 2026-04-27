# 映月工厂 · 极简歌词工坊

**你是这个项目的协作 AI。本文件是你的唯一入口说明，读完即可开始工作，不需要再问任何背景问题。**

---

## 系统是什么

一个把"创作意图"变成 Suno 可粘贴歌词三件套的 CLI 流水线：

```
用户意图 → Claude API 生成歌词 → Python lint 校验 → out/ 输出
```

输出三件套：
- `out/lyrics.txt` — 粘贴进 Suno 的 Lyrics 框
- `out/style.txt`  — 粘贴进 Suno 的 Style 框
- `out/exclude.txt` — 负向风格标签

---

## 核心口令（你看到这些就直接执行，不用追问）

### 生成歌词

用户说：**`生成：[意图]`** 或 **`写歌：[意图]`** 或 **`作词：[意图]`**

你执行：
```bash
python -m apps.cli.main produce "[意图]" --profile urban_introspective --lang zh-CN
```

示例：
> 生成：失恋三个月，深夜睡不着，想发消息又忍住了

→ 你直接运行上面的命令，等输出，然后把 `out/lyrics.txt` 的内容展示给用户。

---

### 带风格生成

用户说：**`生成：[意图] #[风格]`**

| 关键词 | profile 参数 | 适合场景 |
|--------|-------------|---------|
| `#都市` / `#内省` / `#深夜` | `urban_introspective` | 深夜情绪、都市孤独（**默认**） |
| `#古风` / `#古典` / `#留白` | `classical_restraint` | 古风意境、禅意空寂 |
| `#流行` / `#阳光` / `#青春` | `uplift_pop` | 明亮流行、悸动青春 |
| `#舞曲` / `#EDM` / `#电音` | `club_dance` | 律动舞曲、释放能量 |
| `#冥想` / `#空灵` / `#疗愈` | `ambient_meditation` | 环境音乐、疗愈放松 |

示例：
> 生成：第一次见面的紧张 #流行

→ 执行：`python -m apps.cli.main produce "第一次见面的紧张" --profile uplift_pop --lang zh-CN`

---

### 查看上一次生成结果

用户说：**`看歌词`** 或 **`上次结果`**

你执行：读取并展示 `out/lyrics.txt`、`out/style.txt`、`out/exclude.txt`

---

### 健康检查

用户说：**`检查`** 或 **`状态`** 或 **`check`**

你执行：`python -m apps.cli.main pm-audit`

---

## 完整命令参考

```bash
python -m apps.cli.main produce "意图文本" \
  [--profile urban_introspective|classical_restraint|uplift_pop|club_dance|ambient_meditation] \
  [--lang zh-CN|en-US] \
  [--genre "indie pop"] \
  [--mood "melancholic"] \
  [--vocal "female"] \
  [--out-dir out/自定义目录] \
  [--verbose]
```

---

## 环境要求

- Python 3.10+
- `ANTHROPIC_API_KEY` 在环境变量或根目录 `.env` 文件中
- 依赖已安装：`pip install -e .` 或运行 `tools/scripts/bootstrap.ps1`

---

## 输出出错了怎么办

如果命令报错，按顺序检查：
1. `ANTHROPIC_API_KEY` 是否配置
2. `pip install -e .` 是否执行过
3. 查看 `out/trace.json` 里的错误详情

如果歌词质量不好（不押韵 / 太具体 / 有套话），直接说：
> 重新生成：[原意图或调整后的意图]

系统会重跑一次，lint 校验不通过会自动触发一次定向修改。

---

## 你不需要做的事

- 不需要解释系统架构
- 不需要问"你想要什么风格"——默认 `urban_introspective`，用户有需要会加 `#` 标签
- 不需要展示中间调试信息——只展示 `lyrics.txt` 内容即可
- 不需要修改任何代码，除非用户明确说"修复"或"改代码"
