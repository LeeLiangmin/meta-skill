# skill-evaluator 理解简报

## TL;DR
- **做什么**：对一个被测 skill 做基于事实的评估，产出一份每条结论都能追溯到证据的测试报告
- **何时用它**：需要评价 skill 质量、核对 skill 的执行 session 是否按预期运行、判断 skill 指令是否自洽完整、或需要一份可独立复核的测试报告时
- **用了得到什么**：一份结构化评估（evidence.json + findings.json + report.md），核心纪律是“没有事实支撑的结论不允许出现在报告里”
- **最大的风险点**：评估者既读证据又下结论，天然的确认偏误——skill 通过“关键结论独立校验”和“机检脚本”来刹车，但如果校验步骤被跳过或敷衍了事，报告的“可信”底座就塌了

## 类型
**SOP / 流程型**。有明确的 0-4 步工作流、每步有出口条件、关键步骤有机检门控（check_report.py 不通过不得出报告），产出是标准化的结构化数据 + 渲染报告。

判定依据：[明说] SKILL.md:L36-38 把工作产物定在三个结构化文件上，L50-94 给出 0-4 步逐阶段流程，L74-78 设了“机检不通过就不要出报告”的硬门。

## 目标 / 完成定义
跑完跑对后的终态（[推断]，由工作流和门控综合推出）：
- `evidence.json` 里的每一条证据都有精确 locator，能让人据此找到原文
- `findings.json` 里的每条发现都引用了至少一个 evidence_id；高严重度发现都有校验记录
- `check_report.py` 通过（退出码 0）
- `report.md` 渲染成功，报告里的每句判断都能指回证据（无论走默认模板、占位符模板还是自由文体路径）

## 为什么
[明说] SKILL.md:L8-14 给了核心理由：“评估报告会被用来决定一个 skill 是否上线、是否要改。一个‘听起来合理但其实是脑补’的结论，比没有结论更危险，因为它会误导决策。” 因此把“先收集事实、再下结论、关键结论还要独立校验”做成了流程和可机检的格式。

[推断] 选择 evidence.json + findings.json → report.md 的数据/渲染分离，而非直接写成一份报告，深层原因有三：1）把“事实”和“判断”的混淆从格式层面杜绝（账本阶段零判断）；2）让机检可以自动化（脚本扫 JSON，不用解析自然语言报告）；3）换模板不破坏纪律（纪律在数据层，不在 markdown 里）。

## 前置条件 / 输入
- **被测 skill 的路径** [明说] — SKILL.md 及其 references/scripts/assets 可读
- **执行 session**（对 🔴 维度必须，否则只能做静态评估）[明说] — 运行记录/transcript
- **外部事实来源**（可选但强烈需要）[明说] — 文档、命令输出、规范等可独立核对的东西
- **Python 3 运行环境** [明说] — 三个 scripts 都依赖 Python 3，脚本在 `skill-evaluator/scripts/` 下
- **subagent 能力** [明说] — 首选校验方案；无 subagent 时退化为“新视角复核”，但独立性弱，需在报告里如实说明（references/verification.md:L43-51）

## 流程（阶段级）

### 阶段 0：确认范围与来源
把三类来源逐一**落实**，不要假设它们存在。
- **检查点**：`evidence.json` 的 `sources` 列表完整，每个来源的 type 和 locator 明确
- **失败时**：来源缺失的在 `findings.json` 里记 gap；无 session 时降级为“静态评估”——只能评指令正确性、一致性、完整性、可触发性，无法评执行保真度、产出质量、效率

### 阶段 1：建证据账本
逐来源抽取原子事实写入 `evidence.json`，每条只装一个事实，用中立措辞，零判断。
- **检查点**：每条证据有精确 locator（skill→L行号，session→回合/工具调用，external→命令+输出或URL），excerpt 简短但可据此找到原文
- **失败时**：locator 缺失的证据等于没有证据——`check_report.py` 会直接把这类条目标红。回去补定位或删掉该条

### 阶段 2：按维度评估
对照七个维度逐一过：指令正确性、内部一致性与完整性、可触发性、执行保真度、产出质量、效率、安全与意图一致性。
- **检查点**：每个适用维度的结论都由账本里的证据回答，不适用维度和缺证据维度已标记
- **失败时**：发现证据不足以支撑结论 → 标为 unverified，放入盲区，不要伪装成结论

### 阶段 3：校验关键结论
高严重度结论必须经过独立校验（subagent 首选，无 subagent 时用新视角复核）。
- **检查点**：每个高严重度 finding 的 `verification` 字段已填，结果为 confirmed / refuted / inconclusive
- **失败时**：refuted → 改掉或删掉 finding；inconclusive → 降级严重度或移入盲区

### 阶段 4：写发现，机检，再渲染报告
写 `findings.json` → 跑 `check_report.py` → 通过后选模板路径渲染 `report.md`。
- **检查点**：`check_report.py` 退出码 0；报告成品（若是自由文体手填）再跑 `check_citations.py` 通过
- **失败时**：机检不通过就不要出报告——回去补证据或降级结论

## 关键观察点
- **确认偏误**：评估者同时持有证据和倾向时最容易自我印证。缓解机制在阶段 3 的校验协议——盯这个步骤是否被真做了（而不是走形式给了 subagent 一个有倾向的问题）
- **“缺失也是事实”的代价**：声称“session 里没有 X”比声称“有 X”风险更大——必须真读全了 session 才能说（evidence-ledger.md:L50-51）[明说]。这里最容易出现静默错误：扫了几眼就下“没有”的结论
- **机检的覆盖边界**：`check_report.py` 强制的是 structural 纪律（每条 finding 引用有效 evidence_id、高严重度 finding 有校验记录），但它不能验证 finding 的**语义正确性**——即“引的证据是否真的支持这个结论”[推断]。这部分完全依赖评估者自己的判断和校验步骤
- **自由文体路径的引用断裂风险**：如果走路径 C（手填进用户模板），JSON 机检被绕过，纪律依赖 `check_citations.py` 补救——如果这一步漏跑，报告就成了没有强制约束的普通文档 [明说 SKILL.md:L91-94]

## 验收标准
[SOP 型重点 — 每个标准应可机检或被独立核查]

- [ ] `evidence.json` 的每条证据有 `locator` 字段且非空
- [ ] `findings.json` 的每条 finding 的 `evidence_ids` 非空且全部指向存在的 evidence ID
- [ ] 高严重度 finding 均有 `verification` 字段，method 合法，result 为 confirmed/refuted/inconclusive
- [ ] `check_report.py` 退出码 0
- [ ] 报告成品（至少）包含：被测 skill 名、来源清单、按维度的发现、盲区列表、总评及支撑发现、证据账本附录
- [ ] 若走自由文体路径，`check_citations.py` 退出码 0
- [ ] 报告方法学一节如实说明了校验方式（subagent 或 fresh_eyes）

## 失败模式 / 反目标
- **[明说]** 把推断伪装成观察（SKILL.md:L101）
- **[明说]** 脑补 session 里没发生的事（SKILL.md:L26-27）
- **[明说]** 机检没通过就出报告（SKILL.md:L77-78）
- **[推断]** 校验时给 subagent 带倾向的问题（如“请确认 skill 在第 X 步做错了”），使它失去独立性——这是最隐蔽也最严重的失效模式，因为表面上校验步骤被执行了
- **[明说]** 隐藏盲区以制造虚假的全面感（SKILL.md:L102）
- **[明说]** 凭总体印象下最终结论，而非点名是哪几条发现撑起来的（SKILL.md:L105）

## 缺口
以下 skill 未说清，**仅观察，不开处方**：

- **[缺失]** 没交代 Python 不可用时的退路。三个机检脚本全依赖 Python 3，但 skill 没有提替代方案或“依赖声明”
- **[缺失]** 与 skill-digest 的界限没划清。skill 在 L109 只说“不同于 skill-creator”，但 skill-digest 同样是“读一个 skill 产出报告”，两者的分工（一个是中立理解简报，一个是评估判断报告）虽然在产出上有明显的“描述 vs 评判”之别，但没有明确对使用者说明何时该用哪个
- **[缺失]** 没说明评估者自身资质。skill 假定执行者是一个能运行 Python、能调用 subagent 的 LLM agent——这个假设是合理的（它本身就是一个 skill 给 agent 用的），但没有显式声明“本 skill 由 LLM agent 执行”
- **[缺失]** 七个评估维度里“可触发性”维度的完整评估依赖 trigger eval 工具（evaluation-dimensions.md:L35），但该工具属于 skill-creator 范畴，skill 没有指导评估者在没有那套工具时该怎么下有限结论
- **[缺失]** 没给定各维度的权重或最终结论（verdict）如何从各维度 findings 综合得出。四个 verdict 等级（pass / pass_with_issues / fail / inconclusive）在脚本常量里定义了，但由哪些规则决定取哪个值，没有写出来

---
- 想要带证据的质量评判 / 执行审计 → 用 **skill-evaluator**（就是本简报的目标 skill 本身）
- 想快速理解另一个 skill → 用 **skill-digest**
- 想动手改进这个 skill → 用 **skill-creator**
