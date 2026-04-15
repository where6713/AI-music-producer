# 核心业务逻辑范围清单（人工手写强制）

> 目标：把“核心业务逻辑”落成可追溯、可机判、可审计的清单，防止将关键判断外包为通用生成。
> 上位约束：`AI-music-producer PRD_v1.1.md`、`one law.md`

---

## 1. 核心业务逻辑判定标准

满足任一条即判定为核心业务逻辑（必须人工手写，禁止仅靠模板拼装）：

1. 直接改变业务结论或用户成本（如摩擦度结论、升降调建议、抽卡前风险判断）。
2. 直接决定安全边界或权限边界（如自检工具的允许/禁止执行策略）。
3. 直接决定核心 IP 算法有效性（如中文填词物理拦截、音色相似度计算）。
4. 直接决定核心 JSON 产物字段含义与阈值（如 `friction_report.json`、`lyrics.json`）。

---

## 2. 核心逻辑范围（模块 / 函数 / 算法）

### 2.1 `acoustic_analyst`（PRD 5.1）
- 模块：`src/producer_tools/business/acoustic_analyst.py`
- 核心函数范围：声学特征提取、音域/共振峰/动态特征汇总、`voice_profile.json` 关键字段生成。
- 核心算法范围：基频与共振峰提取、MFCC 特征、音色嵌入映射逻辑。
- 人工手写强制：特征选择规则、异常音频处理策略、字段阈值定义。

### 2.2 `style_deconstructor`（PRD 5.2）
- 模块：`src/producer_tools/business/style_deconstructor.py`
- 核心函数范围：参考曲结构拆解、BPM/调性/段落与轨道能量输出、`reference_dna.json` 生成。
- 核心算法范围：结构分段、轨道特征映射、人声对照特征抽取。
- 人工手写强制：结构标签规则、能量曲线统计口径、字段落库规则。

### 2.3 `friction_calculator`（PRD 5.3）
- 模块：`src/producer_tools/business/friction_calculator.py`
- 核心函数范围：三层瀑布判定、摩擦归因、调和建议生成、`friction_report.json` 输出。
- 核心算法范围：硬约束判定、音色相似度评分、综合摩擦指数聚合。
- 人工手写强制：评分公式、阈值边界、判词（`verdict`）映射规则。

### 2.4 `lyric_architect`（PRD 5.4）
- 模块：`src/producer_tools/business/lyric_architect.py`
- 核心函数范围：五步流水线控制、违规检测、重写触发、`lyrics.json` 输出。
- 核心算法范围：开闭口音检测、声调碰撞检测、烂梗密度统计与迭代上限控制。
- 人工手写强制：高音可唱性判据、声调风险阈值、烂梗判定词典与重写策略。

### 2.5 `prompt_compiler`（PRD 5.5）
- 模块：`src/producer_tools/business/prompt_compiler.py`
- 核心函数范围：提示词编译、约束拼装、风险提示注入、`compile_log.json` 生成。
- 核心算法范围：字段映射、约束优先级决策、约束消解顺序。
- 人工手写强制：编译规则表、规则仲裁机制、负面约束注入策略。

### 2.6 `post_processor`（PRD 5.6 / 10.1）
- 模块：`src/producer_tools/business/post_processor.py`
- 核心函数范围：后期链路编排、拼接与自然化处理、最终交付参数输出。
- 核心算法范围：动态去齿音、总线处理、片段拼接决策。
- 人工手写强制：链路顺序、参数区间、失败回退逻辑。

### 2.7 `shell_probe` / `py_eval`（PRD 6.1）
- 模块：`src/producer_tools/self_check/shell_probe.py`、`src/producer_tools/self_check/py_eval.py`
- 核心函数范围：可执行命令白名单/黑名单判定、隔离执行与超时控制。
- 核心算法范围：风险级别分流、执行前确认策略、隔离边界规则。
- 人工手写强制：白名单规则、危险操作拦截规则、隔离策略。

---

## 3. 非核心范围（可 AI 辅助）

以下内容可使用 AI 辅助生成，但不得反向覆盖第 2 节核心规则：
- 文档模板与报告框架。
- 通用 CLI 展示文案与解释层文本。
- 不包含决策策略的脚手架代码与样板类型定义。

---

## 4. 可验证判定标准（机判）

### 4.1 触及核心逻辑的判定
- 检查命令：`git diff --name-only -- docs/governance/core-logic-checklist.md src/producer_tools/business src/producer_tools/self_check`
- 通过条件：若变更命中核心模块路径，则 PR 必须包含“人工手写说明 + 阈值/规则变更说明”。

### 4.2 PRD 可追溯性判定
- 检查命令：对变更说明执行 `Select-String -Pattern 'PRD\s*(5\.1|5\.2|5\.3|5\.4|5\.5|5\.6|6\.1|10\.1)'`
- 通过条件：每个核心模块改动至少命中 1 条对应 PRD 条款。

### 4.3 人工手写约束判定
- 检查命令：`Select-String -Path 'docs/governance/core-logic-checklist.md' -Pattern '人工手写强制'`
- 通过条件：核心模块段落均存在“人工手写强制”行，且内容非空。

### 4.4 合规结论
- 通过：核心变更有 PRD 映射、有人工手写说明、有规则阈值说明。
- 失败：任一核心模块缺失 PRD 映射，或缺失人工手写说明，或将核心算法描述为“自动生成即可”。

---

## 5. 本清单使用规则

1. 本文件是“核心业务逻辑范围”的唯一治理归属文件。
2. 新增核心模块时，必须先补本清单再落实现代码。
3. 核心阈值变更必须附审计证据并可复跑验证命令。
