---
name: skill-evaluator
version: 1.2
description: 测评、评估或审计一个已有的 skill，并生成一份基于事实、每条结论都有事实支撑的测试报告。当用户想评价某个 skill 的质量、检查 skill 是否按预期工作、核对 skill 执行 session（运行记录/transcript）中的真实行为、判断 skill 的指令是否正确/一致/完整、或需要一份可追溯到证据的 skill 测试报告时，务必使用本 skill。触发语包括但不限于"测评这个 skill""评估一下这个 skill""审计 skill""这个 skill 写得对不对""这个 skill 跑得怎么样""帮我给 skill 出一份测试报告""核对一下这次运行有没有按 skill 来"——即使用户没有明确说"测评"二字也应使用。注意：本 skill 用于**评估其它 skill**，不用于创建或编写新 skill（创建 skill 属于 skill-creator 的职责）。触发词区分："测评/评估/审计/测试报告/写得对不对/跑得怎么样"触发本 skill；"理解/读懂/搞清楚/快速了解"触发 skill-digest。
---

# Skill Evaluator

本 skill 的唯一目标：对一个**被测 skill**做出可信的评估，并输出一份测试报告。它能可信，是因为它强制一条纪律——

> **没有事实支撑的结论不允许出现在报告里。**

报告里的每一句判断，都必须能指回某个具体证据：被测 skill 文件的某几行、执行 session 里的某个事件、或某个明确的外部事实来源。做不到这一点的话，那句话就不是"发现"，而是"待核验的猜测"或"盲区"，必须如实标注，绝不能伪装成结论。

这条纪律不是道德要求，而是工程要求：评估报告会被用来决定一个 skill 是否上线、是否要改。一个"听起来合理但其实是脑补"的结论，比没有结论更危险，因为它会误导决策。所以本 skill 把"先收集事实、再下结论、关键结论还要独立校验"做成了流程和可机检的格式，而不是靠自觉。

## 三种证据来源

评估只能建立在以下来源上，每条事实都要标明出自哪一种：

1. **被测 skill 本身**（`skill`）——SKILL.md 及其 references/scripts/assets。这是"skill 声称自己会做什么、要求什么"的来源。定位用文件名 + 行号，如 `SKILL.md:L40-45`。
2. **执行 session**（`session`）——skill 实际运行时的记录/transcript（jsonl、markdown 日志、对话导出等任何形式）。这是"实际发生了什么"的来源。定位用回合/工具调用，如 `run.jsonl:turn 7 / tool_call=read_file`。
3. **其它明确的外部事实来源**（`external`）——文档、规范、命令实际输出、网页等可独立核对的东西。定位用 URL+抓取日期或命令+输出，如 `https://docs… (fetched 2026-06-17)`。

每一类来源都可以有**多个**：多段 session（如同一 skill 的几次运行）、多份外部文档都正常，数量不限，评估中途发现需要新事实也可随时追加进账本。来源的"种类"固定是这三类（这正是分类的意义），但"数量"自适应——`evidence.json` 的 `sources` 和 `evidence` 都是列表。

如果某个来源用户说会给但实际没有（比如"评估一下这个 skill 跑得怎么样"但没给 session），**不要脑补运行情况**：把它记成盲区，相关维度标注为"未评估——缺少 session"，并可以主动提出补一个（见"工作流"第 0 步）。

## 三种结论状态

报告里每条陈述只能是以下三种之一，且必须标明：

- **observed（观察到）**——来源里直接写着的事实，附原文摘录 + 定位。
- **inferred（推断）**——由若干 observed 事实经过明确推理得出的结论。必须写出推理链，且引用所依据的证据。
- **unverified（未核验）**——证据不足以支撑的说法。**绝不能**作为发现呈现，只能放进"盲区与局限"里，明确标注为假设。

## 工作流

工作产物放在被测 skill 同级的 `<skill-name>-eval/` 目录下。核心中间产物是两个结构化文件 `evidence.json`（证据账本）和 `findings.json`（发现），最终交付物 `report.md` 由它们渲染而来。把"事实"和"结论"做成分离的数据，是这条纪律落地的关键：先把证据钉死，再谈结论。

### 第 0 步：确认范围与来源

先把三类来源逐一**落实**，不要假设它们存在：

- 被测 skill 的路径——`view` 一下确认 SKILL.md 可读，记下它引用的 references/scripts/assets 是否真实存在。
- session——确认拿到了运行记录，确认能读。若没有 session：要么向用户说明只能做"静态评估"（指令正确性、一致性、完整性、可触发性可评，但执行保真度、产出质量、效率无法评），要么在环境允许时主动**跑一次**被测 skill 来产生 session（这本身也是一条有用的证据）。
- 外部事实来源——记下用户指定了哪些；评估中途若需要新的外部事实，按需补充并入账本。

把这些写进 `evidence.json` 的 `sources` 列表。请求过但拿不到的，先记成 `findings.json` 里的 gap。

### 第 1 步：建证据账本（只记事实，不下判断）

逐个来源抽取**原子事实**，每条给一个稳定 ID 写进 `evidence.json`。此阶段保持中立、零判断——只记"skill 第 40 行要求先读 SKILL.md""session 第 7 回合没有读 SKILL.md 就直接写文件了"这类可核对的事实，不要写"skill 没被遵守"这种结论（那是后面的事）。摘录尽量精确但简短（避免大段复制）。账本格式与抽取技巧见 `references/evidence-ledger.md`。

### 第 2 步：按维度评估

对照 `references/evaluation-dimensions.md` 里的维度逐一过：指令正确性、内部一致性与完整性、可触发性、执行保真度、产出质量、效率、安全与意图一致性。每个维度本质是一个问题（如"session 里实际按 skill 指令走了吗？偏离在哪、偏离是帮了还是坏了事？"），答案必须由账本里的证据回答。维度的具体问法、需要哪类证据、什么算通过/失败，都在该 reference 里。

### 第 3 步：校验关键结论

不是所有结论都需要独立校验，但**高影响结论必须校验**。在以下情况启用校验（细节见 `references/verification.md`）：

- 该结论若成立会显著改变最终结论（高严重度发现）；
- 来源之间相互矛盾；
- 结论依赖对 skill 文本的微妙解读，容易看花眼；
- 你怀疑自己有确认偏误（你既读了证据又想下结论，容易自我印证）；
- 这是个尚未落地到外部来源的外部事实。

**校验首选 subagent**：给 subagent **只**提供原始来源片段和一个精确的是非问题，**不要**把你的结论告诉它——独立性正是校验的价值所在。subagent 返回 confirmed / refuted / inconclusive 及它自己找到的证据，记回账本。**没有 subagent 时**退化为"新视角复核"：从零重新打开原始来源，忽略自己之前的笔记，重新独立回答那个精确问题——这比独立校验弱，要在报告方法学里如实说明。

### 第 4 步：写发现，机检，再渲染报告

把每条结论写进 `findings.json`：每个 finding 必须带至少一个 `evidence_ids`；inferred 的必须有 `reasoning`；高严重度的必须有 `verification`。然后**先机检再出报告**：

```bash
# Linux/macOS
python3 scripts/check_report.py <skill-name>-eval/evidence.json <skill-name>-eval/findings.json

# Windows
python scripts\check_report.py <skill-name>-eval\evidence.json <skill-name>-eval\findings.json
```

这个脚本机械地强制本 skill 的核心纪律：任何引用了不存在证据的发现、任何没有证据的发现、任何没校验的高严重度发现、任何缺定位的证据，都会被标红。**机检不通过就不要出报告**——回去补证据或降级结论。通过后渲染：

```bash
# Linux/macOS
python3 scripts/render_report.py <skill-name>-eval/evidence.json <skill-name>-eval/findings.json -o <skill-name>-eval/report.md

# Windows
python scripts\render_report.py <skill-name>-eval\evidence.json <skill-name>-eval\findings.json -o <skill-name>-eval\report.md
```

报告模板有三条路径，**纪律不变**——因为它强制在上面的 JSON 数据上，而非模板上，所以换模板不削弱可信度。按用户需求选（细节见 `references/report-templates.md`）：

- **默认模板**：不传 `--template`，用内置 `assets/report-template.md`。
- **自定义占位符模板**：用户能给"固定结构 + 几个填空位"时，把格式写成带 `{{占位符}}` 的 markdown（空白起手模板见 `assets/report-template-blank.md`），渲染时 `--template 用户模板.md`。脚本只填认识的占位符，多余的会告警。
- **用户的自由文体模板**（没有占位符的现成文档/格式）：先 `--emit-fragments fragments.json` 导出每段自带 `[Ex]` 引用的现成片段，手填进用户文档的对应小节，**手填时不得丢引用、不得新增无证据的结论**；填完后必须对成品再跑一道引用校验：

```bash
# Linux/macOS
python3 scripts/check_citations.py <skill-name>-eval/最终报告.md <skill-name>-eval/evidence.json

# Windows
python scripts\check_citations.py <skill-name>-eval\最终报告.md <skill-name>-eval\evidence.json
```
```

这一步把"每条结论必有证据"重新强加到**成品**上——手填绕过了 JSON 机检，靠它补回纪律。

无论哪条路径，最后用 `present_files` 交付报告。

## 写报告时的硬规矩（违反即返工）

- **每条发现都要能指回证据。** 想说一句话却找不到证据，就去找证据、或交给 subagent 校验、或把它降级成"盲区里的假设"并明确标注——三选一，不能直接断言。
- **区分观察与推断。** 别把"我觉得"写成"事实如此"。推断要把链条摊开，让读者能自己复核。
- **盲区要写出来。** 没评到的、证据不足的，明说"未评估/未核验"及原因。隐藏盲区等于制造虚假的全面感。
- **不偏不向。** 你既不为这个 skill 站台也不黑它。证据指向哪就写哪，包括证据相互矛盾时如实呈现矛盾。
- **严重度分级。** 每条发现标 high / medium / low，依据是"它对'这个 skill 能不能用'的判断影响多大"。
- **结论（verdict）由发现支撑。** 最终判断（通过/有问题可用/不通过/证据不足）必须点名是哪几条发现撑起来的，不能凭总体印象。

## 何时不用本 skill

要**创建**或**编写**新 skill、优化 skill 描述的触发率——那是 skill-creator 的事。本 skill 只做"对一个既有 skill 下评估、出报告"。如果用户其实是想边做边改 skill（创建+迭代），把 skill-creator 介绍给他们。

## 参考文件

- `references/evidence-ledger.md` — 证据账本的 schema、三种来源的定位规范、从 session 抽取事实的技巧。
- `references/evaluation-dimensions.md` — 七个评估维度，每个维度的问法、所需证据、通过/失败判据与常见失败模式。
- `references/verification.md` — 校验协议：何时必须校验、subagent 独立校验的提示词模板、无 subagent 时的退化方案、结果如何入账本。
- `references/report-templates.md` — 报告的三条路径（默认/占位符/自由文体）、占位符清单、如何把内容映射进用户的现成格式。
- `references/findings-schema.md` — findings.json 的完整数据结构、字段说明、与机检规则的对应关系。
- `assets/report-template.md` — 内置默认报告模板。
- `assets/report-template-blank.md` — 可直接复制改造的占位符空白模板。
- `scripts/check_report.py` — 报告机检器（在 JSON 数据上强制"无证据不结论"）。
- `scripts/render_report.py` — 由 evidence.json + findings.json 渲染报告（支持默认/自定义模板、导出片段）。
- `scripts/check_citations.py` — 对最终成品做引用校验（手填自定义模板后必跑）。
