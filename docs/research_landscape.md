# CausalPilot / TRACE：研究版图与申请匹配分析

> 调研截止：2026-07-19（Asia/Shanghai）
> 目标：为长江商学院 AI 智能产业实验室 RA / 博士后申请确定一个兼具可证伪研究问题、产业价值和高完成度 Demo 的 Agentic AI 项目。
> 证据标记：**[事实]** 表示来源直接陈述；**[推断]** 表示基于多个事实做出的项目判断；**[建议]** 表示尚待实验验证的设计选择。
> 重要边界：本文是定向、可复核的桌面调研，不是穷尽式系统综述；“未发现同类组合”不等于“世界首创”。

## 1. 执行结论

**[建议] 最值得做的项目仍是 CausalPilot：一个用证据而不是语言自信来分配行动权的业务实验智能体。** 核心方法命名为 **TRACE — Trajectory-calibrated Risk-aware Agentic Causal Experimentation**。

冻结后的研究命题是：

> 在实验曝光预算和人类注意力预算有限时，显式追踪模型、因果、数据与环境四类轨迹风险，能否比直接 LLM、ReAct、固定因果流水线或口头置信度阈值，更好地在“继续诊断、运行小规模探针、询问人类、分群部署、暂停/回滚、拒绝行动”之间分配决策权，从而在相同覆盖率下减少有害部署，并在相同风险上限下提高策略价值？

这不是一个已经被结果证明的结论，而是项目需要通过可执行 benchmark 证伪或支持的假设。

**[推断] 该选题的申请价值来自三个交集：**

1. 它承接实验室已经公开展示的电商现场实验、异质性处理效应、因果分析与 Agentic AI 方向；
2. 它与 KP-Agent 的“业务 Agent + 工具 + 反馈”连续，但研究对象从关键词动作优化转向更上游的“何时有资格行动”；
3. 它把 SEED 中的授权、升级、审计和治理结构变成可执行的序贯决策与评测，而不是再画一层多 Agent 架构图。

## 2. 调研方法与可信度

**[事实]** 本次优先检索和深读以下原始来源：AINB 与 CKGSB 官方页面、论文作者发布的 arXiv/ACL/ACM 页面、官方数据集页面、作者 GitHub 仓库。对技术主张不采用聚合博客作为证据。重点核验了：实验室方向、KP-Agent、SEED、Agent UQ、轨迹不确定性、Agent abstention、因果/实验型 Agent、公开随机数据以及可复用开源工具。

**[事实]** 关键来源存在三个应主动披露的限制：

- KP-Agent 的主要收益数字来自历史数据上的模拟评估，而不是线上随机实验；
- SEED 自称仅进行了轻量级 feasibility test，不能被表述为已验证的治理决策系统；
- 2026 年 5–7 月出现的 CausaLab、CausalSteward、AgentAbstain 等仍是近期预印本，适合界定前沿和缺口，但结论需要后续复现。

## 3. AINB / 孙天澍团队方向与申请匹配

### 3.1 官方方向

- **[事实]** CKGSB 官方将实验室使命表述为结合科技与商业、理论与实践，与企业、行业和政府共同推进产业数字化，覆盖技术战略、商业设计、人才组织、行业标准和产业政策；研究同时强调数据科学/AI 等技术与数字战略、敏捷组织、监管治理等商业设计。[CKGSB 实验室介绍](https://www.ckgsb.edu.cn/faculty/article/index/1207)
- **[事实]** AINB 当前公开的四组 initiatives 是 **Enterprise AI Transformation Architecture、AI Innovation Diffusion & Growth、AI Labor and Social Impact、Next-Generation AI Architects**。[AINB Initiatives](https://ainb.ai/en/initiatives)
- **[事实]** AINB 的项目组合明确出现推荐系统现场实验、异质性政策匹配、可扩展因果分析以及“大数据 + 小实验”的自适应因果推断主题。[AINB Initiatives](https://ainb.ai/en/initiatives)、[AINB Publications](https://ainb.ai/en/publications)
- **[事实]** 2026 年 5 月 CKGSB 官方访谈中，孙天澍把在原有流程上增加 AI 的“+AI”与围绕智能体重构业务系统的“AI+”区分开，并强调“场景、数据、智能体”和面向产业的 AI 架构师。[CKGSB 访谈](https://www.ckgsb.edu.cn/about/article_detail/79/25235.html)

### 3.2 CausalPilot 的匹配逻辑

| 官方信号 | CausalPilot 对应交付 | 判断类型 |
|---|---|---|
| 技术与商业、理论与实践结合 | 自然语言业务目标进入可审计的实验—部署闭环；结果用业务与风险指标共同评估 | **[推断]** |
| 企业 AI 转型架构 | 明确人、Agent、统计工具和审批/回滚之间的权责边界 | **[推断]** |
| 推荐、因果、异质性处理效应 | 使用公开随机/带 propensity 的电商广告数据，做 OPE、uplift 与分群决策 | **[推断]** |
| 下一代 AI 架构师 | 不只调用模型，而是设计状态机、工具契约、风险门、审计轨迹和失败策略 | **[推断]** |
| AI-native、快速落地（来自用户提供的招聘材料） | 一键 Demo、可运行代码、自动评测、技术报告和 90 秒视频形成完整作品证据 | **[建议]** |

**[推断]** 对申请而言，最有说服力的叙事不是“我做了很多 Agent”，而是“我发现了真实业务 Agent 的授权缺口，做出了可测的系统，并清楚区分线上因果证据、离线估计和模拟结果”。

## 4. 与团队近期工作的连续性和边界

### 4.1 KP-Agent：最直接的邻近工作

**[事实]** KP-Agent 由 Hou-Wan Long、Yicheng Song、Zidong Wang、Tianshu Sun 提出，发表于 CIKM 2025。它把搜索广告关键词裁剪建模为 contextual bandit，使用领域工具、长期记忆和反思，并让 LLM 生成可执行代码处理表格数据。[KP-Agent 论文](https://arxiv.org/abs/2601.05257)

**[事实]** 论文报告：

- 分析超过 50 万条搜索广告记录；过滤后的评估环境覆盖 45 个 campaign、278 个关键词、21 天和约 220 万次曝光；
- 主要评估是基于历史数据的 simulation；论文明确说明真实 A/B 测试成本高且需要广告主内部许可；
- 在其模拟假设下，累计利润相对不同基线的提升范围为 2.46%–49.28%；49.28% 是相对 regression-driven baseline 的上界，不是线上生产利润提升；
- 模拟假设包括固定日预算和活跃关键词间的均匀预算分配，基础模型为 GPT-4.1 nano。

**[推断]** KP-Agent 已经占据“LLM + 领域工具 + 记忆 + bandit 优化搜索广告动作”的位置。CausalPilot 若只做“LLM 调 EconML/OBP 后给策略”，会显得是相邻包装。真正互补的贡献应是：

> 在动作优化器外再引入一个可审计的自治边界：证据不足时，系统是否应补数据、探针、询问、局部上线、暂停或拒绝？

### 4.2 SEED：结构表示而非已完成的决策策略

**[事实]** SEED（Structural Encoding for Experimental Discovery）由 Yingjie Zhang、Chun Feng、Weizhang Zhu、Tianshu Sun 提出，用 typed actor-flow graph 表示人—AI/多 Agent 实验条件，支持描述条件、比较结构新颖性和在可行性/治理约束下生成候选设计。[SEED 论文](https://arxiv.org/abs/2605.17746)

**[事实]** 论文把 AI→human escalation、human reviewer、confidence threshold、audit requirement 等作为 actor-flow 或 governance moderator 的例子；同时明确其经验验证只是 medical-triage 设计任务上的轻量级 feasibility contrast，并强调 SEED 不能自行证明实验有效性，仍需方法与伦理审查。

**[推断]** 因而 CausalPilot 与 SEED 的最佳关系是“执行层互补”：SEED 描述谁向谁移交权力，TRACE 研究在什么证据与风险条件下发生移交。不能声称 TRACE 是 SEED 的官方实现，也不能把 SEED 中的阈值示例表述为已经验证的最优门控。

## 5. 2025–2026 前沿：真正的研究缺口在哪里

### 5.1 Agent 不确定性与 abstention

| 工作 | 已证实贡献 | 对 CausalPilot 的启示 | 仍未覆盖的空间 |
|---|---|---|---|
| [Uncertainty Quantification in LLM Agents, ACL 2026](https://aclanthology.org/2026.acl-long.738/) | **[事实]** 指出现有 UQ 多集中于单轮 QA，并提出 estimator 选择、异构实体、交互动态、细粒度 benchmark 四项 Agent 特有挑战 | 风险必须随工具观察和历史轨迹更新，不能只问模型“你有多自信” | 不提供业务因果实验与部署策略 |
| [UProp](https://arxiv.org/abs/2506.17419) | **[事实]** 将序贯决策不确定性拆成当前决策内部不确定性与从先前步骤继承的 extrinsic uncertainty，并在 AgentBench/HotpotQA 评测 | TRACE 应保存 risk lineage，避免每一步独立打分 | 目标仍是一般多步决策 UQ，不处理业务实验预算和行动权 |
| [SAGE-Agent / ClarifyBench](https://arxiv.org/abs/2511.08798) | **[事实]** 对工具参数维护结构化不确定性，以 POMDP/EVPI 选择澄清问题，并衡量问题成本 | “只问一个最有价值的问题”可借鉴 VOI，而不是无差别 HITL | 关注工具参数歧义，不是因果证据或部署风险 |
| [AgentAbstain](https://arxiv.org/abs/2607.10059) | **[事实]** 263 组 act/abstain 配对任务、42 个可执行环境；17 个模型中最佳 paired accuracy 为 59.5%，并识别“先执行不可逆动作、再声称拒绝”的 post-hoc abstention | 必须在 commit action 之前设确定性门，评测要读取真实 action trace | 不包含实验设计、因果估计或业务价值优化 |

**[推断]** 这些结果共同支持一个方向：Agent 可靠性正在从“输出是否正确”转向“轨迹何时应继续、询问、停止或行动”。CausalPilot 的可辨识位置是把这种 abstention/clarification 能力接入因果证据、实验预算和业务 guardrail。

### 5.2 因果与实验型 Agent

| 工作 | 已证实范围 | 与 CausalPilot 的差异 |
|---|---|---|
| [Causal-Copilot](https://arxiv.org/abs/2504.13263) / [GitHub](https://github.com/Lancelot39/Causal-Copilot) | **[事实]** 自动化数据检查、算法/超参数选择、因果发现、因果推断、bootstrap 不确定性与报告生成；仓库为 MIT | 是“完成因果分析”的 copilot；公开设计未定义基于实验/人工预算的 deploy/probe/rollback 策略与 harmful-deployment benchmark |
| [Causal Agent](https://arxiv.org/abs/2408.06849) / [GitHub](https://github.com/Kairong-Han/Causal_Agent) | **[事实]** 工具、记忆和多步推理处理 causal tabular QA；仓库为 MIT | 评测核心是变量/边/图/效应问答准确率，而非决策闭环 |
| [CausalSteward](https://arxiv.org/abs/2607.01936) | **[事实]** 用多 Agent divide–conquer–combine、RAG、条件独立检验和 HITL 组装高维因果图 | 聚焦高维 causal discovery 和专家知识，不负责业务上线门控 |
| [CausaLab](https://arxiv.org/abs/2605.26029) | **[事实]** 让 Agent 在合成 SCM 实验室中主动干预，分别评估预测与机制恢复；发现强模型会过早停止，预测正确也可能恢复错误机制 | 说明“实验选择本身”和轨迹审计重要；其任务是科学机制发现，不是异质性业务策略与风险约束 |
| [LeGIT](https://arxiv.org/abs/2503.01139) | **[事实]** 用 LLM 世界知识辅助因果发现中的 intervention target selection | 选择干预变量，不处理是否上线、询问或回滚 |
| [AgentA/B](https://arxiv.org/abs/2504.09723) | **[事实]** 用 LLM persona 在网页上模拟 A/B 测试用户行为；案例为 1,000 个 LLM agents，并与聚合人类行为方向比较 | 模拟用户不能替代真实随机证据；CausalPilot 应明确模拟/离线/真实证据等级 |
| [Budget-Constrained Causal Bandits](https://arxiv.org/abs/2604.26169) | **[事实]** 近期预印本把 uplift、探索和预算 pacing 统一成序贯分配，并在 Criteo 上做离线实验 | 与 RUN_PROBE/预算策略邻近；CausalPilot 的差异必须落在多风险自治、人类查询、abstain/rollback 与审计，而非再发明一个 bandit |

**[推断]** 经本次定向检索，尚未发现一个公开系统同时把以下六项作为第一等对象：轨迹级四类风险、确定性统计工具、因果/实验信息动作、人类注意力成本、分群部署/回滚/拒绝、配对的业务 harmful-deployment 评测。这是一个**候选差异化组合**，不是未经系统综述即可宣称的“首创”。

## 6. 可复用开源项目与 build-vs-buy 边界

| 项目 | 可直接复用 | 不应重复造轮子 | CausalPilot 需要新增 |
|---|---|---|---|
| [Open Bandit Pipeline](https://github.com/st-tech/zr-obp)（Apache-2.0） | OBD loader、Replay、DM/IPW/SNIPW/DR 等 OPE 接口 | propensity/OPE 基础实现 | 轨迹状态、风险门、动作决策与审计 UI |
| [DoWhy](https://github.com/py-why/dowhy) | model–identify–estimate–refute、敏感性/稳健性检查 | 因果识别和 refutation 基础 | 将诊断转成可校准风险证据，而不是让 LLM读数表 |
| [EconML](https://github.com/py-why/EconML) | DML、异质性处理效应估计 | CATE estimator | 分群安全门、预算与选择性部署评测 |
| [Causal-Copilot](https://github.com/Lancelot39/Causal-Copilot)（MIT） | 竞品参考：工具注册、算法选择、因果报告 | 不复制“自动因果分析聊天框”定位 | 以 action authority 和 risk–coverage 为中心的产品交互 |
| [Causal Agent](https://github.com/Kairong-Han/Causal_Agent)（MIT） | 竞品参考：因果工具 + 记忆 + 多步推理 | 不以 causal QA 准确率作为主贡献 | 序贯实验与有害行动评测 |
| [AgentAbstain](https://github.com/AntiQuality/agentabstain)（代码 MIT；数据 CC BY 4.0） | commit trace + terminal response 的双重评测思想、paired act/abstain 设计 | 不重新定义一般 abstention taxonomy | 把 paired design 迁移到可计算的业务因果场景 |

**[建议]** 第一版用小而透明的自有实现包住这些统计原语。LLM 只负责假设、工具编排、行动候选和面向人的解释；功效、SRM、balance、overlap、置信区间、uplift/OPE、漂移和硬约束必须由确定性代码返回结构化证据。

## 7. 数据集核验与真实性边界

### 7.1 Open Bandit Dataset（OBD）

**[事实]** ZOZO 官方说明 OBD 来自 ZOZOTOWN 上 Uniform Random 与 Bernoulli Thompson Sampling 两种策略的 A/B 数据，共约 2,600 万次曝光，包含匿名上下文、被选 item/action、真实 propensity、位置、时间戳和 click outcome；收集跨 7 天、3 个 campaign。[ZOZO 数据页](https://research.zozo.com/data.html)、[OBP 官方仓库](https://github.com/st-tech/zr-obp)、[NeurIPS 数据论文](https://arxiv.org/abs/2008.07146)

**可做：**

- OPE estimator 的离线估计、策略价值比较、支持度/有效样本量诊断；
- 用不同 policy/campaign/time slice 构造分布漂移；
- 使用官方仓库每个 campaign-policy 10,000 条的小样本做无下载 smoke test。

**不可做或必须改名：**

- outcome 是点击，不能称为真实 conversion、profit 或收入；
- 静态日志不是 CausalPilot 实际发出的 30,000 次线上曝光；Demo 必须标记 **OFFLINE REPLAY** 或 **SIMULATION**；
- 官方页面与仓库要求引用论文，但本次未在数据页定位到独立、明确的数据许可证文本。OBP 软件的 Apache-2.0 许可证不能自动等同于完整数据的许可。默认不把完整 OBD 重新分发进仓库。

### 7.2 Criteo Uplift Prediction Dataset

**[事实]** Criteo 官方页面说明原始版本由多次广告 incrementality randomized trials 汇总，25,309,483 行，字段列表含 12 个匿名特征、treatment、conversion、visit、exposure，treatment ratio 约 0.846。[Criteo 官方数据页](https://ailab.criteo.com/criteo-uplift-prediction-dataset/)

**[事实] 关键勘误：** 官方同时说明原始版本因不同广告主的 incrementality level 非均匀、特征分布可区分广告主而发生 leak；官方随后发布 unbiased 版本，共 **13,979,592** 行，treatment ratio 约 0.85。项目默认应使用这个去偏版本，而不是为了“数据更大”使用有泄漏的 2,530 万行版本。

**[事实]** 页面给出的许可为 **CC BY-NC-SA 4.0**。因此：

- 可用于非商业研究 benchmark，并需署名；
- 不把完整数据提交到 GitHub；
- 若发布由该数据衍生的可识别材料，需单独复核 ShareAlike/NonCommercial 条款；项目代码本身可保持自己的软件许可证，但不要暗示数据也随软件许可发布。

**可做：** uplift/CATE、策略分群、bootstrap CI、处理/对照 balance、有限预算 targeting 的离线评测。

**不可做或必须限定：**

- 没有个体反事实真值，不能声称知道每个用户的“真实 uplift”；
- 离线 RCT 数据不能复现真正在线、自适应地连续发出实验流量；
- 没有利润字段，真实数据结果应表达为 visit/conversion 的增量估计，而不是利润。

### 7.3 三层证据设计

| 层级 | 用途 | 能宣称什么 | 不能宣称什么 |
|---|---|---|---|
| 可控 SCM/业务模拟器 | 90 秒交互 Demo；精确 harmful action、regret、drift ground truth | 在指定生成过程与 seed 下的真实计算结果 | 真实用户/企业收益 |
| Criteo unbiased RCT 日志 | 外部 uplift、分群、区间与政策评估 | 对公开随机日志的离线估计 | CausalPilot 发起了线上实验 |
| OBD 随机/TS 日志 | OPE、propensity、支持度和漂移 | 对点击策略的离线/在策略对照 | 转化、利润、真实部署 |

**[建议]** 前端始终显示证据徽标：`SIMULATED GROUND TRUTH`、`PUBLIC RCT — OFFLINE`、`LOGGED BANDIT — OPE`，并把 `estimate`、`confidence interval`、`ground truth` 分栏，避免炫酷视觉掩盖证据等级。

## 8. 冻结的研究假设与可证伪性

### RQ1：选择性自治

**[建议]** 在匹配部署覆盖率时，TRACE 是否降低 ground-truth harmful-deployment rate？在匹配风险上限时，是否提高 policy value？

### RQ2：信息动作

**[建议]** 与静态阈值相比，基于预期信息价值的 `RUN_PROBE` / `ASK_HUMAN` 是否以更少实验曝光和人工问题达到同等或更低 regret？

### RQ3：轨迹风险

**[建议]** 继承过去工具失败、证据冲突和漂移状态的风险表示，是否比当前步骤口头 confidence 有更好的 Brier/ECE、risk–coverage 和错误行动识别？

### RQ4：结构贡献

**[建议]** 去掉动态校准、实验动作、人类查询或 VOI 后，性能是否按预期退化？若不退化，TRACE 的相应组件应被否定或简化，而不是事后改指标。

## 9. 可在申请周期内真实完成的范围

### 9.1 两周级可交付

- **[建议]** 一个有 ground truth、支持 probe/drift/human answer 的确定性业务模拟器；
- **[建议]** overlap、ESS、balance、功效/CI、简单 uplift、OPE、漂移的结构化工具；
- **[建议]** 显式状态机和四风险向量，支持 8 类动作及完整 JSONL 审计；
- **[建议]** direct LLM、ReAct+同工具、fixed pipeline、verbal confidence、无 TRACE、always-deploy、always-ask/abstain 等基线接口；
- **[建议]** 一个固定 seed、90 秒内可重复的 3D 控制室；
- **[建议]** 无 API key 的 deterministic demo mode；有模型时再开启真实 coordinator；
- **[建议]** 自动从结果 JSON/Parquet 生成表格，不在 README 手填优势数字。

### 9.2 不应在首版承诺

- 真实企业流量接入或线上 RCT；
- 已证明 TRACE 在产业中提升利润；
- 大规模训练 trajectory risk critic；
- 通用 causal discovery；
- 对任意数据自动保证因果识别有效；
- 经过真实部署验证的 probability calibration；
- 世界首个/行业领先等无法由本次定向检索证明的宣传语。

## 10. 主要风险与应对

| 风险 | 严重度 | 具体表现 | 应对 |
|---|---:|---|---|
| 研究新颖性被快速前沿挤压 | 高 | AgentAbstain、CausaLab、CausalSteward 已覆盖 abstention/实验/因果 Agent 的不同切面 | 把贡献冻结为“业务因果证据下的行动权分配”，避免泛化为“Agent 会拒绝” |
| 将离线日志伪装成在线实验 | 高 | UI 显示实时粒子流，观众误以为真实用户曝光 | 永久证据徽标；模拟器、RCT 离线、OPE 三种模式独立 |
| 风险分数是假精确概率 | 高 | 没有 calibration set 却显示“92% 安全” | 未校准时只叫 `risk index`；只有通过 held-out reliability evaluation 后才显示概率 |
| Criteo 数据泄漏与许可 | 高 | 使用 25.3M 旧版得到虚高结果；或把 NC-SA 数据上传 GitHub | 默认 unbiased 13.98M；下载脚本 + checksum；不分发完整数据 |
| 指标不可识别 | 高 | 在真实日志上报告个体 true uplift / true harmful deployment | ground-truth 指标只在模拟器；真实日志使用 OPE/held-out estimate 并明确是 surrogate |
| Demo 大于研究 | 中 | 3D 粒子很炫，但动作由硬编码时间线触发 | 每个视觉变化绑定实际 audit event；同一后端可 headless replay；演示 seed 固定但结果由引擎计算 |
| LLM 随机与 API 不稳定 | 中 | 现场模型超时或输出 schema 错误 | deterministic demo coordinator；严格 JSON schema；模型只影响候选/解释，不绕过硬门 |
| 多重检验和分群过拟合 | 中 | 挑出“安全子群”其实是偶然显著 | 预注册 segment、holdout、multiplicity correction、报告覆盖率和最小样本 |
| 统计工具误用 | 中 | overlap、SRM、OPE estimator 在错误数据模式下被调用 | 工具声明前置条件；adapter 级 schema；不满足时返回 structured refusal |

## 11. 最终定位语与申请叙事

**英文一句话：**

> CausalPilot is an evidence-gated experimentation agent that earns deployment authority by reducing causal, data, model, and environment risk—not by verbalizing confidence.

**中文一句话：**

> CausalPilot 让业务 Agent 通过实验、校准与审计获得行动权，而不是凭语言能力宣称自己有行动权。

**[推断]** 这条叙事与实验室的产业 AI 架构、实验因果传统和近期 Agent 工作高度连续，同时又把作品区分于普通 RAG、研究报告 Agent、多 Agent 公司和纯因果分析聊天框。

## 12. 核心原始来源索引

1. [CKGSB AI 智能产业实验室介绍](https://www.ckgsb.edu.cn/faculty/article/index/1207)
2. [AINB Initiatives](https://ainb.ai/en/initiatives)
3. [AINB Publications](https://ainb.ai/en/publications)
4. [CKGSB：从“+AI”到“AI+”访谈](https://www.ckgsb.edu.cn/about/article_detail/79/25235.html)
5. [KP-Agent](https://arxiv.org/abs/2601.05257)
6. [SEED: Agents for Experiments, Experiments for Agents](https://arxiv.org/abs/2605.17746)
7. [Uncertainty Quantification in LLM Agents, ACL 2026](https://aclanthology.org/2026.acl-long.738/)
8. [UProp](https://arxiv.org/abs/2506.17419)
9. [SAGE-Agent / ClarifyBench](https://arxiv.org/abs/2511.08798)
10. [AgentAbstain](https://arxiv.org/abs/2607.10059) 与 [官方代码](https://github.com/AntiQuality/agentabstain)
11. [Causal-Copilot](https://arxiv.org/abs/2504.13263) 与 [官方代码](https://github.com/Lancelot39/Causal-Copilot)
12. [Causal Agent](https://arxiv.org/abs/2408.06849) 与 [官方代码](https://github.com/Kairong-Han/Causal_Agent)
13. [CausalSteward](https://arxiv.org/abs/2607.01936)
14. [CausaLab](https://arxiv.org/abs/2605.26029)
15. [LeGIT](https://arxiv.org/abs/2503.01139)
16. [AgentA/B](https://arxiv.org/abs/2504.09723)
17. [Budget-Constrained Causal Bandits](https://arxiv.org/abs/2604.26169)
18. [ZOZO Open Bandit Dataset](https://research.zozo.com/data.html)
19. [Open Bandit Pipeline](https://github.com/st-tech/zr-obp) 与 [数据论文](https://arxiv.org/abs/2008.07146)
20. [Criteo Uplift Prediction Dataset](https://ailab.criteo.com/criteo-uplift-prediction-dataset/)
21. [DoWhy](https://github.com/py-why/dowhy) 与 [论文](https://arxiv.org/abs/2011.04216)
22. [EconML](https://github.com/py-why/EconML)
