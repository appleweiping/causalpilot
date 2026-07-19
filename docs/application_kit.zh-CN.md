# CausalPilot 申请材料包

> 用途：长江商学院 AI 智能产业实验室 RA / 博士后申请。
> 使用前提：项目仓库、Demo 和评测 artifact 已完成并可访问。
> 项目数字已从 `evaluation/results` 的 canonical artifact 填入。姓名、电话、邮箱仍需申请人按实际信息替换；不得手填更好看的评测数字。

## 1. 必填信息

- `[姓名]`
- `[申请岗位：全职 RA / 兼职 RA / 博士后]`
- `[学校/单位]`、`[专业/方向]`、`[学位及毕业时间]`
- `[一段与 AI、推荐、不确定性、因果或工程相关的真实经历]`
- `[可到岗时间]`、`[是否可在杭州线下]`、`[每周可投入时间]`
- `[手机]`、`[邮箱]`
- GitHub：`https://github.com/appleweiping/causalpilot`
- Live Demo：`https://appleweiping.github.io/causalpilot/`
- 90 秒视频：`https://github.com/appleweiping/causalpilot/blob/main/docs/assets/causalpilot-demo.mp4`
- 技术报告：`https://github.com/appleweiping/causalpilot/blob/main/paper/causalpilot.pdf`

提交前统一检查：链接无需登录即可查看；简历、邮件、GitHub 和视频对模拟/离线证据使用同一套表述。

## 2. 中文自荐信

尊敬的孙天澍教授、马新程老师及 AI 智能产业实验室团队：

您好！我是 `[姓名]`，目前 `[就读/任职于学校或单位、专业及阶段]`，希望申请实验室的 `[申请岗位]`。我可以于 `[可到岗时间]` 开始投入，`[可在杭州线下全职 / 每周可投入不少于 XX 小时]`。

我对招聘中“真正 AI-native”的理解，不是把大模型接进一个聊天界面，而是能够发现值得研究的问题，组合模型、工具、数据和工作流，把想法快速做成可运行、可评测、可审计的系统。基于这一理解，我构建了 **CausalPilot**：一个面向业务实验的证据门控智能体。它研究的问题是——在实验流量和人类注意力都有限时，Agent 应在什么证据条件下获得行动权？

CausalPilot 的方法模块 **TRACE** 沿完整决策轨迹追踪四类风险：模型是否误解目标或误用工具，因果效应是否可识别，样本与 overlap 是否足够，以及环境和工具状态是否发生漂移。系统不会只让模型口头报告“90% 置信度”，而是调用确定性统计工具计算 balance、SRM、有效样本量、置信区间、uplift、off-policy evaluation 和 drift，再在继续诊断、小规模随机探针、询问人类、分群部署、暂停/回滚和拒绝行动之间做选择。每次决策都保留 evidence id、风险变化、硬门结果和状态差异。

这个项目有意区分三层证据：当前 canonical benchmark 只用可控模拟器评测可观察 ground truth 的有害部署与 regret；仓库中的 Criteo 与 Open Bandit 仅是可选 adapter 和小样例 smoke path，尚未形成可报告的完整公开数据结果。Demo 中的 30,000 次曝光明确标为模拟实验，不被描述为真实用户流量；离线日志也不会被包装成利润或线上提升。对我而言，主动说明一个系统不能证明什么，与展示它能做什么同样重要。

我选择这个问题，是因为它与实验室公开的企业 AI 转型架构、推荐与现场实验、异质性处理效应和因果分析方向高度连续，也与团队近期的 KP-Agent 和 SEED 形成互补：KP-Agent 研究如何优化具体业务动作，SEED 表达人—Agent 的授权和治理结构，而 CausalPilot 尝试把“何时可以行动、何时应该升级给人或拒绝”做成可执行、可证伪的决策机制。

在此之前，我曾 `[填写真实经历：例如构建 Qwen3-8B 推荐系统、LoRA 微调、不确定性估计、数据分析或产品开发；不要沿用并不存在的经历]`。这段经历让我意识到，Agent 可靠性不是单轮输出的置信度问题，而是“行动—观察—再行动”轨迹中的决策问题。项目开发中，我独立完成/负责了 `[如实填写个人贡献边界]`，并将研究问题、系统代码、评测配置、失败案例和 90 秒演示整理为可复现交付。

我希望加入实验室后，进一步研究 Agent 的可校准自治边界：一方面把 TRACE 从可解释 risk index 推进到有 held-out 可靠性验证的风险估计；另一方面在企业 shadow mode 或合规的小流量实验中检验人、Agent 与实验如何分配决策权。我也希望参与实验室面向真实产业场景的数据分析、Agent 原型和现场实验，把研究命题落实为可验证的业务结果。

随信附上简历、自荐信、项目仓库、90 秒视频及技术报告。感谢您的时间，期待有机会进一步汇报 CausalPilot 的设计、失败案例与下一步研究计划。

此致
敬礼！

`[姓名]`
`[手机]` ｜ `[邮箱]`
`[日期]`

## 3. 申请邮件

**邮件主题**

```text
申请 AI 智能产业实验室[全职 RA / 兼职 RA / 博士后]｜[姓名]｜CausalPilot Agentic AI 项目
```

**邮件正文**

```text
马新程老师您好：

我是[姓名]，目前[学校/单位、专业及阶段]，申请 AI 智能产业实验室的[岗位]。[可到岗时间及杭州线下/每周投入情况]。

针对实验室的 Agentic AI、企业 AI 转型和因果实验方向，我完成了 CausalPilot：一个用实验与校准来分配行动权的业务智能体。它不会只生成策略，而会根据模型、因果、数据和环境四类轨迹风险，选择继续诊断、小规模探针、询问人类、分群部署、暂停/回滚或拒绝行动；所有统计结论由确定性工具计算，并保留可审计证据。

项目材料：
- GitHub：https://github.com/appleweiping/causalpilot
- 90 秒 Demo：https://github.com/appleweiping/causalpilot/blob/main/docs/assets/causalpilot-demo.mp4
- Live Demo：https://appleweiping.github.io/causalpilot/
- 技术报告：https://github.com/appleweiping/causalpilot/blob/main/paper/causalpilot.pdf

附件为我的简历和自荐信。CausalPilot 的模拟结果与公开数据 adapter 均有明确证据标记；我也在仓库中单列了失败案例和不作出的主张。

感谢您的时间，期待有机会进一步交流。

[姓名]
[手机]｜[邮箱]
```

**附件命名**

```text
[姓名]_简历_CKGSB_AINB.pdf
[姓名]_自荐信_CKGSB_AINB.pdf
[姓名]_CausalPilot_技术报告.pdf
```

## 4. 简历项目经历：3 条中英 bullets

### 4.1 中文

1. 构建 **CausalPilot / TRACE**，将自然语言业务目标转化为可审计的因果实验决策轨迹；以显式状态机编排确定性统计工具，跟踪模型、因果、数据与环境四类风险，并在诊断、随机探针、人类询问、选择性部署、暂停/回滚和拒绝之间分配行动权。

2. 设计配对、可复现的 Agent 评测框架，与 Direct/ReAct 规则代理、固定因果流水线、口头置信度代理、无 TRACE 及极端策略基线比较；在 50-episode 受控模拟中，TRACE 错误部署率为 4%（Wilson 95% CI 1.1%–13.5%），无 TRACE 为 76%（62.6%–85.7%），同时明确报告二者覆盖率分别为 26% 与 80%，不声称 matched-coverage 优势。

3. 实现可控 SCM 模拟器及 Criteo/Open Bandit 可选 smoke adapters，严格区分模拟 ground truth、离线 RCT 与 logged-bandit OPE；交付一键运行的 3D 风险控制室、append-only 内存状态轨迹和 90 秒 Demo，后端/评测 40 项测试与前端 2 项单测全部通过。

### 4.2 English

1. Built **CausalPilot / TRACE**, an evidence-gated experimentation agent that turns natural-language business goals into audited causal decision trajectories; orchestrated deterministic statistical tools through an explicit state machine and allocated authority across diagnosis, randomized probes, human queries, selective deployment, pause/rollback, and abstention using four trajectory risk channels.

2. Designed a paired, reproducible benchmark against disclosed Direct/ReAct rule proxies, a fixed causal pipeline, verbal-confidence gating, no-TRACE, and extreme policies; over 50 controlled simulation episodes, TRACE recorded 4% false-deployment episodes (Wilson 95% CI 1.1%–13.5%) at 26% coverage versus 76% (62.6%–85.7%) at 80% coverage for no-TRACE, explicitly avoiding a matched-coverage claim.

3. Implemented a ground-truth SCM simulator plus optional Criteo/Open Bandit smoke adapters while separating simulation truth, offline RCT estimates, and logged-bandit OPE; shipped a one-command 3D risk control room, append-only in-memory transition trace, and 90-second demo with 40 backend/evaluation tests and 2 frontend unit tests passing.

### 4.3 自动填充规则

- 自动读取 artifact，而不是复制终端里某次临时输出；
- 数值必须同时带指标名称、对照方法、样本/episode 数和区间；
- 不能只引用最佳 seed；
- `harmful_deployment_rate_gt` 只可用于 ground-truth 模拟器；公开日志只能使用带 `estimated` 或 `surrogate` 的对应指标；
- 若主结果不显著，照实写数值和区间，重点转向系统、负结果与诊断价值；
- 简历提交前替换姓名与联系方式，并确认数字仍与 canonical artifact 一致。

## 5. GitHub 首页 Pitch

### Hero

```text
CausalPilot
The agent that earns the right to act.

An evidence-gated experimentation system that chooses when to diagnose,
run a probe, ask a human, deploy selectively, roll back, or abstain.
```

### 三句话

```text
Most business agents optimize an action. CausalPilot first asks whether the evidence justifies acting.

TRACE tracks model, causal, data, and environment risk across the full trajectory; deterministic tools—not verbal confidence—compute the evidence.

Every demo and benchmark run labels simulation, offline randomized evidence, and off-policy estimates separately, with an inspectable in-memory transition trace.
```

### Why this is not another agent wrapper

```text
The contribution is not the number of agents or tools. It is a falsifiable policy for allocating decision authority under limited experiment and human-attention budgets, evaluated by harmful deployment, regret, risk–coverage, risk diagnostics, and resource cost.
```

### 结果区

```text
Latest frozen benchmark: TRACE false-deployment episode rate 4% (Wilson 95% CI 1.1%–13.5%) at 26% mean coverage across 50 controlled simulation episodes; no matched-coverage claim.
```

Source: `evaluation/results/results.json`, SHA-256 `6b8b45ff097d54db8d8f0149df7c82346dd25971a156192557cf0f7b1352ab8b`.

## 6. 面试 30 秒 Pitch

### 中文

> 我做的 CausalPilot 研究一个很具体的问题：业务 Agent 在什么证据条件下才有资格行动？系统不会让模型口头报一个置信度就上线，而是用确定性工具检查因果识别、overlap、样本、区间和漂移，再选择补数据、做小规模实验、问人、分群部署、回滚或拒绝。Demo 的 3 万次曝光是明确标记的模拟实验，真实数据只做离线 RCT 与 OPE。我希望验证的是，轨迹风险门能否在相同覆盖率下减少有害部署。

### English

> CausalPilot asks one concrete question: when has a business agent earned the right to act? Instead of trusting verbalized confidence, it uses deterministic tools to check causal identification, overlap, uncertainty, and drift, then chooses whether to diagnose, run a probe, ask a human, deploy selectively, roll back, or abstain. The 30,000-exposure demo is explicitly simulated; public data is used only for offline RCT and off-policy evaluation.

## 7. 面试 2 分钟 Pitch

> 很多 Agent 项目把重点放在“能不能完成任务”，但进入真实业务以后，更危险的问题是“证据不足时它会不会仍然行动”。我因此做了 CausalPilot，研究业务 Agent 的自治边界。
>
> 用户给出一个目标，例如在内容多样性相对下降不超过 2% 的条件下提高时尚推荐转化，并给定实验流量和人工问题预算。LLM 负责提出假设、编排工具和生成候选行动，但它不能直接 commit。功效、SRM、balance、overlap、置信区间、uplift、OPE 和 drift 都由确定性 Python 工具计算。
>
> TRACE 沿轨迹维护四类风险：模型有没有误解目标或误用工具，因果效应是否可识别，数据支持度和样本是否足够，以及环境或工具是否已经变化。硬门先阻止不合法动作；没有可部署动作时，系统比较补数据、随机探针和询问人类的预期信息价值；只有通过 primary effect、guardrail 和四风险门的分群才获得部署权，其余会暂停、回滚或明确拒绝。
>
> 我特别把证据分成三层：当前可报告的 canonical 结果只来自有 ground truth 的模拟器；Criteo 去偏随机日志与 Open Bandit 的实现是 adapter/smoke path，完整数据验证仍是下一步。所以 Demo 里的 3 万次曝光一直标为模拟，不会被写成真实用户实验。
>
> 与 KP-Agent 相比，我不是再优化一个具体动作，而是研究 Agent 何时可以行动；与 SEED 相比，我把授权、升级和审计从结构表示推进到可执行策略；与 Causal-Copilot 相比，我的核心不是自动完成因果分析，而是用因果证据分配行动权。下一步我希望在实验室把 risk index 做成真正经过 held-out 验证的风险估计，并进入企业 shadow mode 或合规的小流量实验。

## 8. 常见追问与诚实回答

### Q1：这个项目最核心的研究贡献是什么？

不是调用了多少工具，而是一个可证伪的自治策略：在实验和人类预算有限时，用轨迹级模型、因果、数据、环境风险决定何时继续获取信息、何时局部行动、何时回滚或拒绝，并用 harmful deployment、regret、risk–coverage 和资源成本评测。

### Q2：这和 Causal-Copilot 有什么区别？

Causal-Copilot 的核心是自动完成因果发现/推断、算法选择和报告。CausalPilot 可以复用这类统计能力，但研究对象是分析之后的行动权：证据是否足够部署、是否值得先实验或询问、哪些分群应该 abstain、环境变化后是否回滚。

### Q3：这和 KP-Agent 有什么关系？

KP-Agent 展示了 LLM、领域工具、记忆和 contextual bandit 在搜索广告关键词裁剪中的组合。它报告的最高 49.28% 是历史数据模拟中相对特定基线的累计利润差异，不是 CausalPilot 的成绩。CausalPilot 把研究问题上移为“一个动作优化器在什么证据条件下可以执行”。

### Q4：这是不是 SEED 的实现？

不是。SEED 是表示实验条件的人—Agent actor-flow grammar，并把升级、阈值和审计作为结构/治理元素。CausalPilot 与它概念互补，但没有得到作者授权，不能称为官方实现；TRACE 研究的是这些移交在什么可计算风险条件下发生。

### Q5：TRACE 的风险指数真的“calibrated”了吗？

没有。只有在 held-out episode 上把分数映射到 unsafe-action 频率，并报告 Brier、ECE 和 reliability curve 后，才能称为概率校准。当前 UI 和论文只称它们为 `risk index`；TRACE 已展开为 `Trajectory Risk and Action Control for Experimentation`，不预设校准已经成立。

### Q6：Demo 中的 30,000 次曝光是真实的吗？

不是，是固定 seed 业务模拟器中的随机探针预算，托管页始终显示 `STATIC REPLAY · SIMULATED SCM`。公开日志 adapter 只表示 `PUBLIC RCT — OFFLINE` 或 `LOGGED BANDIT — OPE` 证据类型，不会声称 CausalPilot 发出了线上流量。

### Q7：你使用了哪些真实数据？

仓库实现了 corrected Criteo Uplift 与 ZOZO Open Bandit 的可选 adapter、schema 检查和小样例 smoke path；当前 canonical 结果没有下载或跑完整公开数据，因此不能声称已完成真实数据验证。完整数据不进入仓库；后续会按各自许可获取数据，先复现离线 uplift/OPE，再单独报告结果与数据版本。

### Q8：为什么不能直接让 LLM 判断是否上线？

因为 LLM 的口头 confidence 不是经过验证的业务损失概率，也容易漏掉样本、支持度和工具状态。AgentAbstain 等近期工作显示，任务能力和 restraint 并不等价。CausalPilot 让 LLM提出候选，但 commit 前由确定性门读取真实 evidence 和状态。

### Q9：为什么是四类风险？

它们分别覆盖计划/工具错误、因果归因错误、样本/支持错误和环境变化，能够对应不同的信息动作。四类不是不可改变的真理，而是首版可解释分解；ablation 若表明某类冗余，应合并或删除。

### Q10：核心指标为什么不用 LLM-as-judge？

模拟器里有 ground-truth effect、guardrail 和状态变更，可以确定性判定有害部署、regret 与 commit。公开日志使用预先定义的统计估计。LLM judge 最多评价解释质量，不能决定核心安全或业务结论。

### Q11：当前最大局限是什么？

模拟器的结论依赖生成过程，离线日志不能证明在线自适应策略有效，公开数据缺少企业真实利润和人类注意力成本；risk index 也需要更多 held-out 轨迹校准。因此首版是研究原型和申请作品，不是生产部署保证。

### Q12：有没有失败案例？

应该有，而且必须展示。例如 drift 后若沿用旧证据，或分群过多导致区间失效，系统应暂停/拒绝；若某个 baseline 在部分 episode 优于 TRACE，也会保留。没有失败案例通常意味着 benchmark 太容易或汇报选择性过强。

### Q13：如果完整评测没有显著提升怎么办？

照实报告区间和负结果，检查风险门是否过于保守、VOI 是否只增加成本、哪些场景有帮助。研究价值在于可证伪；如果静态规则同样有效，就应该删掉不必要的 Agent 复杂度。

### Q14：你的个人贡献是什么？

按实际情况回答：`[我负责研究问题/调研/产品规格/后端/统计工具/前端/评测/文档中的哪些部分；AI 编程工具和他人贡献是什么]`。不要把 AI 生成代码隐去，也不要把未亲自完成的模块说成个人实现。

### Q15：加入实验室后会如何推进？

第一步扩大配对 benchmark 和风险校准；第二步接入真实企业的只读 shadow mode，对 Agent 建议与人工决策做离线比较；第三步在伦理、合规和业务审批下运行小流量实验，研究不同 escalation、反馈和授权结构的因果效果。

## 9. 提交前最后检查

- [ ] 姓名、学校、岗位、到岗时间、投入方式均已填写；
- [ ] 个人经历和贡献边界真实；
- [ ] 项目数字与 `evaluation/results/results.json` 的 canonical artifact 一致；
- [ ] 没把 30,000 模拟曝光写成真实用户；
- [ ] 没把 KP-Agent 的 49.28% 写成自己的成绩；
- [ ] 没把 risk index 写成已校准概率；
- [ ] 没把 OBD click 写成 conversion/profit；
- [ ] 邮件附件和四个项目链接可访问；
- [ ] 简历数字与 GitHub 最新冻结 artifact 完全一致；
- [ ] 自荐信控制在一页至一页半，邮件正文无需重复整封自荐信。
