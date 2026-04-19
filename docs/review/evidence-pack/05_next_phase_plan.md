## Next Phase Scope (Post-Ready)

### Goal
在不影响当前 Ready 结论的前提下，进入下一阶段的质量强化与技术债收敛，聚焦可验证改进与低风险交付。

### Phase-2 Workstreams

1) **歌词业务质量强化（PROD 延续项）**
- 增加 3 组真实业务输入样本（中文）并沉淀长期回归基线。
- 扩展开口音命中统计：按段落输出命中率与异常行列表。
- 提升 vocal cues 策略可控性：支持按 section 配置命中策略（如 pre-chorus 必须含 inhale）。

2) **证据自动化与审计一致性**
- 生成 evidence-pack 的自动校验脚本（字段完整性、路径存在性、analysis/output 对齐检查）。
- 在 CI 增加 evidence lint（非阻断起步，观察一轮后再转阻断）。
- 固化 PR 模板：强制填写 run URL、commit、P0/P1 变更摘要。

3) **dotenv 初始化技术债治理（P1）**
- 梳理 dotenv 初始化入口，统一到单点加载（CLI 启动层优先）。
- 清理业务模块内分散加载逻辑，避免重复读取与环境漂移。
- 补充回归测试：确保单点初始化后工具链行为不回退。

### Deliverables
- `docs/review/evidence-pack/` 新增第二阶段样本与对照记录。
- 技术债治理记录：`docs/governance/` 下新增 dotenv 治理说明与验收项。
- 对应测试与 CI 证据（pytest + quality-gates）。

### Exit Criteria
- 新增样本在开口音与 vocal cues 指标上达到既定阈值。
- evidence 自动校验可稳定运行且无误报阻断。
- dotenv 单点初始化完成并通过回归测试。
