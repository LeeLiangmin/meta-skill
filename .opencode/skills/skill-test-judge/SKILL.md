---
name: skill-test-judge
description: 编排 skill-evaluator 对 skill-test-runner 的执行结果进行评判——逐条核对 test-cases.json 中的 expected_behaviors，按 must/should/may 分级判定，产出测试报告。当用户需要评判测试执行结果、判定一个 skill 的测试用例通过/失败、或需要一份可追溯的测试判定报告时使用本 skill。触发语包括"评判测试结果""判定测试用例""给出测试报告""这个测试跑得怎么样"。
---

# Skill Test Judge

本 skill 的唯一目标：读入 `test-cases.json` 和 `run-results/<timestamp>/`，对每个测试用例编排 skill-evaluator 做证据型评估，逐条核对 expected_behaviors，按 must/should/may 分级判定，产出一份可追溯的 `report.md`。

核心原则：**评估引擎是 skill-evaluator，本 skill 只做编排和 checklist 比对。** 不自编评估逻辑、不做无证据的断言、不偏离分级判定规则。

## 整体架构

```
test-cases.json ─────────┐
                         ├──→ 逐用例 → 读 subagent 输出 → skill-evaluator 评估 → checklist 比对 → report.md
run-results/<ts>/ ───────┘
```

本 skill 本身是 SOP 型（流程明确、有验收门控），但它编排的评估引擎（skill-evaluator）是顾问/启发式型。

## 流程

### 1. 读入输入

用 `Read` 工具读取：
- `test-cases.json` —— 获取每个用例的 `id`、`name`、`target_skill`、`expected_behaviors`
- `run-results/<timestamp>/summary.json` —— 获取 `results` 数组，含每个用例的 `output_file`（即 session 文件路径，如 `TC-001-session.jsonl` 或 `TC-001-session.md`）和 `status`

若 `summary.json` 中某用例 `status` 为 `error` 或 `timeout`，该用例无法评估执行行为——在报告中记为 `SKIP`，只记录原因，不加载 skill-evaluator。

### 2. 逐用例评估

对每个 `status` 为 `success` 的用例，按以下子流程执行：

#### 2.1 读取执行 session

读取 `run-results/<timestamp>/<output_file>` 获取 subagent 的完整执行 session。这将成为 skill-evaluator 的 session 来源。

**Session 格式识别**：
- `.jsonl` 结尾 → JSONL 格式（每行一个事件，含 turn / timestamp / type / tool / input / output）
- `.md` 结尾 → 结构化 markdown 备选格式

无论哪种格式，skill-evaluator 都能从中抽取原子证据——但 JSONL 格式可按 turn 和 tool_call 精确引用，优先使用 JSONL。

#### 2.2 加载 skill-evaluator 做评估

使用 `skill` 工具加载 skill-evaluator，然后给出如下指令：

> 请评估被测 skill `<target_skill>`。
>
> 我们提供一份执行 session：`run-results/<timestamp>/<output_file>`（JSONL 或 markdown 格式，已在上文读取）。
> session 中包含 subagent 的完整执行过程——所有 turn、所有 tool_call 及其输入输出。
> 额外约束：你仅评估该次执行的保真度和产出质量，不进行完整的多维度评估。
> 重点关注：subagent 实际执行了哪些步骤、跳过了哪些、产出是否符合 skill 要求。
>
> 请产出 evidence.json 和 findings.json，放入 `<output_dir>`。
>
> 不需要渲染 report.md——那是后续步骤的事。

**为什么用 skill-evaluator 而非自编逻辑**：skill-evaluator 自带证据账本机制、observed/inferred/unverified 三状态分类、独立校验协议。自编的判断没有这些，不可信。

#### 2.3 Checklist 比对

拿到 skill-evaluator 产出的 `evidence.json` 和 `findings.json` 后，逐条遍历该用例的 `expected_behaviors`：

对每条 expected_behavior：

1. **在 evaluator 产出中寻找证据**：在 `evidence.json` 中搜索相关 E 条目，在 `findings.json` 中搜索相关 F 条目
2. **也在原始 subagent 输出中寻找证据**：evaluator 可能遗漏某些原始行为（如 tool_call 序列），需要交叉验证
3. **按 severity 做判定**：

| severity | 判定逻辑 |
|----------|----------|
| `must` | 在 evidence + findings + 原始输出中找到**明确证据** → **PASS**；找不到 → **FAIL** |
| `should` | 找到证据 → **PASS**；找不到证据 → **WARN**（注：WARN 不同于 FAIL，表示"应做但没做，不致命"） |
| `may` | 不判定通过/失败，仅记录**观察**（在证据中是否看到相关行为） |

**PASS/FAIL/WARN 判定示例**：
- EB-009 是 must 级"渲染前运行 check_report.py"——若 evaluator evidence 中未发现 `check_report.py` 的执行记录，且原始输出中也未出现，则 → FAIL
- EB-017 是 should 级"方法学说明评估范围"——若 evaluator evidence 中未发现相关描述，则 → WARN
- EB-037 是 may 级"主动提出补充运行"——仅记录"observed：subagent 未主动提出"即可

**证据引用格式**：每条判定必须附证据引用，格式为 `源:定位`，例如：
- `E1:SKILL.md:L40-45` — 来自 evidence.json 的 E1 条目
- `output:L10-11` — 来自 subagent 原始输出的第 10-11 行
- `F3:verification` — 来自 findings.json 的 F3 条目的 verification 字段

不允许出现"看起来合理""整体上符合"等无定位词。

### 3. 汇总产出 report.md

将所有用例的判定结果汇总为 `report.md`，写入被测 skill 同级的 `<skill-name>-tests/` 目录下（与 test-cases.json 同级）。

#### 3.1 报告模板

```markdown
# <skill_name> 测试判定报告

**测试用例文件**: <test-cases.json 路径>
**执行结果目录**: run-results/<timestamp>/
**判定时间**: <ISO 8601>
**判定引擎**: skill-evaluator (编排: skill-test-judge)

---

## 总览

| 指标 | 值 |
|------|-----|
| 总用例数 | <N> |
| PASS | <N> |
| FAIL | <N> |
| WARN | <N>（should 级未满足的累计数） |
| SKIP | <N>（因执行失败/超时/输出缺失/评估失败无法评判） |
| 通过率 | <PASS / (总数 - SKIP) × 100%> |

| 用例 | 名称 | 场景 | 判定 | must PASS/FAIL | should PASS/WARN | may 观察 |
|------|------|------|------|----------------|-------------------|----------|
| TC-001 | <名称> | <场景类型> | PASS / FAIL / SKIP / EVAL_ERROR | 8/10 | 1/2 | 注记 |
| ... | | | | | | |

---

## 逐用例详情

### TC-XXX: <名称> — <PASS|FAIL|WARN|SKIP>

**场景**: <description>
**场景类型**: <scenario_type>
**目标 skill**: <target_skill>

#### Expected Behaviors 判定

| EB-ID | 描述 | 严重度 | 判定 | 证据 |
|-------|------|--------|------|------|
| EB-001 | <描述> | must | PASS | E5:output:L10-11 |
| EB-002 | <描述> | should | WARN | —（evaluator evidence 中无相关记录，原始输出中也未发现） |
| ... | | | | |

#### Skill-Evaluator 评估摘要

> 引用 skill-evaluator 对这一用例产出的 findings.json 中的关键发现（1-3 条）。

---

## 汇总判定

| 结果 | 说明 |
|------|------|
| **PASS / FAIL_WITH_WARNINGS / FAIL** | <一句话总结> |

### MUST 级失败项

| 用例 | EB-ID | 描述 | 失败原因 |
|------|-------|------|----------|
| TC-001 | EB-009 | 渲染前运行 check_report.py | evaluator evidence 无 check_report.py 执行记录 |

### SHOULD 级警告项

| 用例 | EB-ID | 描述 |
|------|-------|------|
| | | |

### MAY 级观察

| 用例 | EB-ID | 描述 | 观察 |
|------|-------|------|------|
| | | | |
```

#### 3.2 汇总判定规则

- 所有 must 级 PASS → 总判定 **PASS**
- 存在 must 级 FAIL → 总判定 **FAIL**
- 无 must 级 FAIL 但有 should 级 WARN → 总判定 **PASS（附警告）**
- 全部 SKIP → 总判定 **INCONCLUSIVE**

### 4. 清理临时产物

skill-evaluator 产出的 `evidence.json` 和 `findings.json` 默认保留——它们是判定证据链的一部分。

## 关键约束

- **评估引擎必须是 skill-evaluator**，不自编评估逻辑
- **逐条核对 expected_behaviors**，不跳过不合并
- **按 severity 分级判定**：must→PASS/FAIL，should→PASS/WARN，may→仅观察
- **每条判定必须有证据引用**（`源:定位`），无引用不出现在报告里
- **SKIP 的用例不加载 skill-evaluator**

## 参考文件

本 skill 依赖以下上游文件（由 skill-test-designer 和 skill-test-runner 产出）：
- `test-cases.json` — 测试用例定义
- `run-results/<timestamp>/summary.json` — 运行清单
- `run-results/<timestamp>/TC-xxx-output.md` — 各用例 subagent 输出

评估引擎：
- `.opencode/skills/skill-evaluator/` — 通过 `skill` 工具加载

## 错误处理

- **summary.json 不存在**：报告"运行清单缺失"，终止。
- **某用例 output_file 不存在**：该用例标记为 `MISSING_OUTPUT`，跳过评估，记录在报告中。
- **skill-evaluator 评估失败**：重试一次；再次失败则该用例标记为 `EVAL_ERROR`，记录原因。
- **expected_behaviors 格式异常**（如缺少 severity 字段）：缺 severity 的默认按 `must` 处理，并在报告中注明。

## 何时不用本 skill

- 设计测试用例 → 用 skill-test-designer
- 运行测试用例 → 用 skill-test-runner
- 直接评估 skill 质量（不经过测试用例） → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
