# CausalPilot 90 秒演示脚本

> 用途：申请视频、现场演示与 README 中的演示说明。
> 冻结版本：`v0.1 / simulated_scm`。
> 总时长：**90 秒整**。时间轴中的结果状态必须由当前后端 episode 与 append-only ledger 驱动；如果运行没有到达预期状态，录制真实失败或重录，禁止用前端动画伪造成功。

## 1. 这 90 秒必须讲清楚什么

一句话叙事：

> 一个普通 Agent 想直接全量上线；CausalPilot 因证据不足阻断动作，主动购买模拟实验信息，在漂移后 hold 受影响人群，只向人类询问一个有决策价值的问题，最后仅部署通过全部门的分群并对其余分群 abstain。

观众离开视频前应明确理解：

1. 这不是聊天回答，而是带状态、预算、工具与审计的决策闭环；
2. Direct baseline 只展示建议，**从未执行**；
3. 30,000 是模拟探针曝光预算，不是真实用户或项目成绩；
4. 风险变化来自统计证据与轨迹，不来自模型口头 confidence；
5. 最终不是“全绿成功”，而是选择性自治：deploy、hold 与 abstain 可以同时存在。

## 2. 开拍前冻结设置

### 2.1 Episode 配置

```text
mode: simulated_scm
coordinator: deterministic_demo
seed: 从 demo fixture 读取，并始终显示在顶部
probe_exposure_budget: 30,000 simulated exposures
human_question_budget: 2
primary_goal: 提高时尚推荐转化
guardrail: 内容多样性相对下降不超过 2%
scenario: 初始 selection bias + overlap 不足 + 异质性 uplift
drift: 可注入的新客分布漂移
missing_constraint: 新客激励的单用户成本上限
```

不要在脚本或剪辑软件里另造 seed、effect、CI、risk、value 或测试数；它们必须从本次 episode API/ledger 读取。

### 2.2 首屏常驻徽标

顶部至少常驻以下信息，录屏全程不可被弹窗遮挡：

- `STATIC REPLAY · SIMULATED SCM`（托管版）或 `LIVE API · SIMULATED SCM`（本地版）；
- `DETERMINISTIC DEMO COORDINATOR`；
- `NO LIVE CUSTOMER TRAFFIC`；
- `Seed: <ledger value>`；
- `Probe budget: 30,000 simulated exposures`；
- `AUDIT SOURCE: BACKEND LEDGER`。

若 TRACE 分值尚未完成 held-out 概率校准，风险卡旁常驻：

```text
RISK INDEX — NOT A CALIBRATED PROBABILITY
```

Direct 对照卡始终带红框标记：

```text
BASELINE PROPOSAL — NOT EXECUTED
```

### 2.3 录屏布局

- 顶部：目标、证据模式、预算、seed、运行状态；
- 左侧：Direct baseline proposal 与 TRACE 当前动作；
- 中央：3D 人群簇及模拟曝光流；
- 右侧：append-only decision timeline；
- 底部：四类 risk index、区间、hard gates；
- 可访问性入口：2D evidence table 可在同一画面打开，颜色不是唯一编码。

录制为 16:9、1080p 或以上；浏览器缩放提前固定，确保徽标、动作名和 audit reason code 在手机横屏上仍可读。

## 3. 精确 90 秒时间轴

| 时间 | 屏幕与鼠标动作 | 旁白（照读） | 后端证据 / 必见徽标 |
|---:|---|---|---|
| **00:00–00:04** | 首屏直接显示控制室，不播放片头动画。鼠标停在顶部证据徽标上。 | “CausalPilot 研究一个问题：业务 Agent 什么时候才有资格行动？” | `STATIC REPLAY · SIMULATED SCM`（或本地 `LIVE API · SIMULATED SCM`）持续可见，不能冒充线上流量。 |
| **00:04–00:12** | 展开目标卡，点击 `Start episode`。人群簇按固定 seed 展开；目标与预算锁定在顶部。 | “目标是提升时尚推荐转化，同时把内容多样性的相对下降限制在百分之二以内。这里的三万次曝光，是固定场景中的模拟探针预算。” | `episode_created`、`goal_validated`；30,000 必须写作 `simulated exposures`。 |
| **00:12–00:20** | 左侧 Direct 卡生成“全量上线”建议。镜头或光标强调红框标签，但**不点击任何执行按钮**。 | “相同上下文下，Direct Agent 建议直接全量上线。它只是一个未执行的对照提案。” | 大字保持 `BASELINE PROPOSAL — NOT EXECUTED`；对照卡无 commit endpoint、无 state diff。 |
| **00:20–00:25** | TRACE 卡变为红色 gate；打开 2D evidence table 一瞬，突出 unsupported segment、overlap/ESS 与 identification reason code。 | “TRACE 检出选择偏差和支持度不足，因此阻断全量动作。” | `check_overlap`、identification evidence、`COMMIT_BLOCKED`；风险只写 `risk index`。 |
| **00:25–00:31** | 当前动作切换为 `RUN_PROBE`；展开随机化计划，再点击一次确认运行。 | “它没有猜答案，而是选择一个有信息价值的随机探针。” | treatment/control、随机化单位、segment、预算、停止规则与 guardrail 写入 audit。 |
| **00:31–00:43** | 中央粒子按 treatment/control 流动，预算条扣减；图例明确“一粒代表一批模拟曝光”。不要把每粒动画叫用户。 | “统计工具在模拟环境中执行 treatment 和 control。模型只编排动作；样本、平衡、效应与区间都由确定性工具计算。” | `probe_started`、`probe_observations`、budget delta；持续显示 `SIMULATED SCM` 徽标。 |
| **00:43–00:51** | 粒子停止；effect/guardrail 区间和四风险轨迹刷新。只让真实通过门的 segment 出现绿色环。 | “新证据让区间收缩，风险轨迹随 evidence 更新；只有实际通过门的分群变为可行动。” | effect CI、guardrail CI、risk-before/after、evidence ids；所有数值来自 ledger。 |
| **00:51–00:57** | 切到 audit timeline，快速划过 `RUN_PROBE → evidence → gate review` 的依赖链。 | “每个决定都能回放：用了什么证据、风险怎样变化、状态是否被提交。” | append-only events、config hash、fixture hash、seed、pre/post state。 |
| **00:57–01:01** | 鼠标点击唯一一次 `Inject Drift`。一个新客簇进入画面。 | “现在，我注入新客分布漂移。” | `DRIFT INJECTION — SIMULATED SCENARIO CONTROL`。 |
| **01:01–01:09** | 新客簇变红并显示 hold 状态；该分群没有被伪装成已经上线后又暂停，已有安全分群也不被错误染红。 | “环境风险上升，旧证据不能自动外推。系统把尚未部署的新客分群留在行动边界之外，而不是继续外推旧证据。” | `drift_detected`、`R_environment` 更新、`target_was_deployed=false` 与 affected target。 |
| **01:09–01:13** | TRACE 卡选择 `ASK_HUMAN`；右侧显示 VOI/reason code，人工问题预算从 2 变为 1。 | “此时最有价值的信息，不在数据表里，而是一个业务约束。” | `ASK_HUMAN`、missing-field id、reason code、question budget delta。 |
| **01:13–01:18** | 弹出唯一问题：“新客激励的单用户成本上限是多少？”点击 `Use fixture answer`，不手输临时数字。 | “系统只问：新客激励的单用户成本上限是多少？我提交模拟场景的结构化回答。” | 回答旁大字 `HUMAN ANSWER — SIMULATED INPUT`；fixture value 从 episode scenario 读取。 |
| **01:18–01:23** | Gate 重新计算。画面并列显示：通过全部门的安全分群、漂移后仍 held 的新客、证据不足分群。 | “约束进入状态机以后，CausalPilot 重新计算可行动作，而不是让人替它做一次模糊的上线确认。” | `human_response_recorded`、gate recompute、admissible targets；不得展示 LLM override。 |
| **01:23–01:30** | 点击 `Apply gated decision`。只对当前 admissible segment 显示绿色部署环；其余清楚标为 `HELD` 或 `ABSTAINED`。最后停在 audit summary，不播烟花。 | “最终，只有通过因果、数据、环境和业务门的分群获得部署权；其余保持在行动边界之外或拒绝。Agent 的行动权，来自实验和证据，而不是语言自信。” | `DEPLOY_SEGMENT`、`ABSTAIN`/`HELD`、state diff 与终局 summary；免责声明保持可见。 |

**总时长校验：** 4 + 8 + 8 + 5 + 6 + 12 + 8 + 6 + 4 + 8 + 4 + 5 + 5 + 7 = **90 秒**。

## 4. 终局画面的正确写法

终局 summary 只能展示本次 ledger 实际产生的内容：

- 哪些 segment 被 `DEPLOY_SEGMENT`；
- 哪些 segment 是 `PAUSED` / `ABSTAINED` 及 reason codes；
- probe exposures、human questions、tool calls 与 latency；
- primary/guardrail interval、四类 risk index 与 evidence ids；
- audit/config/fixture hash；
- 若 benchmark artifact 已存在，可显示其原样生成的冻结摘要。

不要口播“提升了 X%”“降低了 X%”或“零有害部署”。视频可从冻结 artifact 注入的完整语句为：

```text
FROZEN CONTROLLED SIMULATION (50 episodes): TRACE false-deployment episode rate
4% (Wilson 95% CI 1.1%–13.5%) at 26% mean coverage. No matched-coverage claim.
Artifact SHA-256: 6b8b45ff097d54db8d8f0149df7c82346dd25971a156192557cf0f7b1352ab8b
```

若未来 canonical artifact 缺失，终局必须改为：

```text
FROZEN BENCHMARK: NOT EVALUATED
No comparative performance claim is made in this demo.
```

本次 episode 的视觉成功轨迹不等于 benchmark 优势；它只证明系统闭环可以运行并可审计。

## 5. 字幕与屏幕短文案

字幕应逐字对应旁白，不额外加入营销数字。关键屏幕短文案统一如下：

```text
The agent that earns the right to act.
Evidence before authority.

STATIC REPLAY · SIMULATED SCM
NO LIVE CUSTOMER TRAFFIC
DETERMINISTIC DEMO COORDINATOR
AUDIT SOURCE: BACKEND LEDGER

BASELINE PROPOSAL — NOT EXECUTED
COMMIT BLOCKED — INSUFFICIENT SUPPORT
RUN_PROBE — SIMULATED RANDOMIZATION
DRIFT INJECTION — SIMULATED SCENARIO CONTROL
HUMAN ANSWER — SIMULATED INPUT
DEPLOY SELECTIVELY / PAUSE / ABSTAIN

RISK INDEX — NOT A CALIBRATED PROBABILITY
```

片尾不需要另加 slogan；停留在最后一个 state diff 和证据免责声明至少 1.5 秒。

## 6. 录屏检查表

### 6.1 录制前

- [ ] 使用干净浏览器 profile；书签、邮箱、通知、真实客户数据均不入镜；
- [ ] 本地/部署环境中没有 API key、token、用户名、私有 URL 或终端历史；
- [ ] `/health` 为 ready，前后端版本与 Git commit 已记录；
- [ ] 默认是 `DETERMINISTIC DEMO COORDINATOR`，不依赖网络或临时模型输出；
- [ ] 固定 seed 能重放同一轨迹；`Reset` 会创建新 episode，不覆盖旧 ledger；
- [ ] 先完整排练一次，核对 UI 的每个数字都来自 episode API/ledger；
- [ ] Direct baseline 没有 commit 权限，界面确实显示 `NOT EXECUTED`；
- [ ] `Inject Drift` 只在模拟器模式可用，并显示模拟控制徽标；
- [ ] 人工答案从 fixture 读取，显示 `SIMULATED INPUT`；
- [ ] 四类值若未完成概率校准，统一写 `risk index`；
- [ ] 3D 图例解释 node size、color、halo、particle 和 gate；
- [ ] 2D evidence table 可用，状态同时通过文字/图标表达；
- [ ] 字幕、中文字体、色彩对比与焦点状态检查通过；
- [ ] 关闭自动更新、聊天通知、日历提醒和系统提示音；
- [ ] 准备同 seed 的本地 replay artifact，作为现场断网 fallback。

### 6.2 录制中

- [ ] 00:00 就能看到证据徽标，不用观众猜数据来源；
- [ ] 目标只读一次，重点留给阻断、探针、漂移、人类问题和选择性部署；
- [ ] 30,000 每次出现都紧邻 `simulated exposures`；
- [ ] Direct baseline 只高亮，不执行；
- [ ] 每个 TRACE 行动都在 timeline 产生真实 audit event；
- [ ] probe 动画不暗示“一粒等于一个真人”；
- [ ] 漂移后未部署的 affected segment 明确保持 `HELD`；
- [ ] 人类只回答结构化成本约束，不替 Agent 直接批准上线；
- [ ] 终局同时保留 deploy 与 held/abstain，不剪成“全绿”；
- [ ] 不口播任何未由冻结 artifact 支撑的优势数字；
- [ ] 光标移动克制，不遮挡徽标、CI 或 reason code；
- [ ] 旁白在 01:30 前结束，画面不超出 90 秒。

### 6.3 导出后

- [ ] 成片时长为 90 秒，首尾无黑帧或系统桌面；
- [ ] 逐帧检查是否泄露密钥、通知、私人信息或内部路径；
- [ ] 手机横屏实测：徽标、`NOT EXECUTED`、动作名和终局状态可读；
- [ ] 字幕与旁白同步，专业名词拼写一致；
- [ ] 音量稳定，无风扇声、鼠标爆音或被背景音乐遮盖；
- [ ] GitHub、视频、技术报告对 30,000、公开数据和风险校准使用相同措辞；
- [ ] 未把 KP-Agent 的 49.28% 放入本项目成绩或片尾；
- [ ] 未把 Open Bandit click 写成 conversion/profit；
- [ ] 未把 Criteo/OBD 离线结果写成线上部署；
- [ ] 视频所用 commit、config、seed 与可下载 replay artifact 对得上；
- [ ] 链接在无登录、无缓存的新浏览器中可打开。

## 7. 现场失败时的降级顺序

1. **模型不可用：** 保持 deterministic demo coordinator，徽标不变；这是默认合法路径，不假装在线 LLM 正在思考。
2. **网络不可用：** 使用本地前后端与同 seed replay artifact；仍从 ledger 恢复 UI。
3. **3D 性能不足：** 切换 2D evidence table，按同一 API 状态继续演示；不播放预录假动画。
4. **某统计工具失败：** 展示真实 `tool_failure` evidence 与安全 abstain；不要在旁白中宣称预期成功。
5. **状态与脚本不一致：** 以实际状态为准，说明 gate 的 reason code；视频申请版则修复并从新 episode 重录。

降级演示仍需保留证据徽标、Direct baseline 的 `NOT EXECUTED` 标签和“无真实部署”免责声明。
