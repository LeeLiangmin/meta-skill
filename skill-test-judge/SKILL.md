---
name: skill-test-judge
description: 读取 subagent 自评产物，逐条核对 test-cases.json 的 expected_behaviors，按 must/should/may 分级判定，产出测试报告。触发词：评判测试结果、判定测试用例、测试报告、这个测试跑得怎么样。
license: MIT
compatibility: opencode
metadata:
  version: "1.3"
  author: LeeLiangmin
---

# Skill Test Judge

本 skill 的唯一目标：读入 `test-cases.json` 和 `run-results/<timestamp>/`，读取每个 subagent 的**自评产物**（evidence.json + findings.json），逐条核对 expected_behaviors，按 must/should/may 分级判定，产出一份可追溯的 `report.md`。

核心原则：**subagent 已完成自评（内嵌 skill-evaluator 运行），本 skill 做交叉验证 + checklist 比对 + 汇总。** 不再重复加载 skill-evaluator 做评估——subagent 在自己的上下文里跑 evaluator 远比 judge 事后读文本精确。

## 整体架构

```
test-cases.json ─────────┐
                         ├──→ 逐用例 → 读 subagent 自评 evidence.json + findings.json
run-results/<ts>/ ───────┘            → 交叉验证（比对 session 原文）
                                      → checklist 比对（expected_behaviors）
                                      → report.md
```

**为什么不再由 judge 加载 skill-evaluator**：runner 无法获取 subagent 内部的 tool_call 明细（actor_result 只含最终文本）。但 subagent 在执行时当场加载 skill-evaluator 对自己做自评，evaluator 在 subagent 上下文中有权限看到全部 tool_call、输入输出和 reasoning。judge 直接消费这份自评产物，做交叉验证和汇总。

## 流程

### 1. 读入输入

用 `Read` 工具读取：
- `test-cases.json` —— 获取每个用例的 `id`、`name`、`target_skill`、`expected_behaviors`
- `run-results/<timestamp>/summary.json` —— 获取 `results` 数组，含每个用例的 `output_file`、`eval_dir` 和 `status`

若 `summary.json` 中某用例 `status` 为 `error` 或 `timeout`，subagent 未正常完成，无法评估——在报告中记为 `SKIP`，只记录原因。

### 2. 逐用例交叉验证 + 比对

对每个 `status` 为 `success` 的用例，按以下子流程执行：

#### 2.1 读取 subagent 自评产物

从 `run-results/<timestamp>/<eval_dir>/` 读取：
- `evidence.json` —— subagent 自评产出的证据账本
- `findings.json` —— subagent 自评产出的发现

同时读取 `run-results/<timestamp>/<output_file>`（session 原文）用于交叉验证。

#### 2.2 交叉验证

subagent 的自评可能遗漏或粉饰自己的错误。因此 judge 做轻量交叉验证：

1. **抽查 evidence.json 中的关键 E 条目**：在 session 原文中找对应内容，确认 subagent 的自我引用真实存在（文件路径、行号对得上）
2. **核对 findings.json 的全面性**：有没有明显该发现但没发现的问题？检查 session 原文中是否有违反被测 skill 硬规矩的行为而未被 findings 收录
3. **自评偏差标记**：若发现 self-eval 遗漏或弱化自身错误，在报告中标记为 `self-eval bias detected`，并将 judge 的观察作为补充发现

只做抽查（每用例 2-3 条），不做逐条全量复核——那等于重跑一次 evaluator。

#### 2.3 Checklist 比对

逐条遍历该用例的 `expected_behaviors`，在自评产物中寻找证据：

对每条 expected_behavior：

1. **在 evidence.json 中搜索相关 E 条目**，在 findings.json 中搜索相关 F 条目
2. **也在 session 原文中搜索**：evaluator 可能遗漏某些明显行为，需要直接从原文中找
3. **按 severity 做判定**：

| severity | 判定逻辑 |
|----------|----------|
| `must` | 在 evidence + findings + session 原文中找到**明确证据** → **PASS**；找不到 → **FAIL** |
| `should` | 找到证据 → **PASS**；找不到证据 → **WARN**（"应做但没做，不致命"） |
| `may` | 不判定通过/失败，仅记录**观察** |

**PASS/FAIL/WARN 判定示例**：
- EB-009 是 must 级"渲染前运行 check_report.py"——若 evidence 中无相关条目、session 原文中也未出现，则 → FAIL
- EB-017 是 should 级"方法学说明评估范围"——若 evidence 中未发现相关描述，则 → WARN
- EB-037 是 may 级——仅记录"observed：未主动提出"即可

**证据引用格式**：每条判定必须附证据引用，格式为 `源:定位`：
- `E5:output:L10-11` — 来自 evidence.json 的 E5 条目
- `session:L120-125` — 来自 session 原文第 120-125 行
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
**评估方式**: subagent 内嵌 skill-evaluator 自评 + judge 交叉验证与 checklist 比对

---

## 总览

| 指标 | 值 |
|------|-----|
| 总用例数 | <N> |
| PASS | <N> |
| FAIL | <N> |
| WARN | <N>（should 级未满足的累计数） |
| SKIP | <N>（因执行失败/超时/输出缺失无法评判） |
| self-eval bias | <N>（自评偏差标记数） |
| 通过率 | <PASS / (总数 - SKIP) × 100%> |

| 用例 | 名称 | 场景 | 判定 | must PASS/FAIL | should PASS/WARN | bias |
|------|------|------|------|----------------|-------------------|------|
| TC-001 | <名称> | normal | PASS / FAIL / SKIP | 8/10 | 1/2 | — |
| ... | | | | | | |

---

## 逐用例详情

### TC-XXX: <名称> — <PASS|FAIL|SKIP>

**场景**: <description>
**场景类型**: <scenario_type>
**目标 skill**: <target_skill>

#### Expected Behaviors 判定

| EB-ID | 描述 | 严重度 | 判定 | 证据 |
|-------|------|--------|------|------|
| EB-001 | <描述> | must | PASS | E5:session:L10-11 |
| EB-002 | <描述> | should | WARN | —（evidence 无相关记录，session 原文也未发现） |
| ... | | | | |

#### 自评摘要

> 引用 findings.json 中的关键发现（1-3 条）。

#### 交叉验证

> 抽查结果：E12 条目已确认（session:L45 确实有对应内容）；未发现明显遗漏（或：发现 N 处自评偏差）

---

## 汇总判定

| 结果 | 说明 |
|------|------|
| **PASS / FAIL_WITH_WARNINGS / FAIL** | <一句话总结> |

### MUST 级失败项

| 用例 | EB-ID | 描述 | 失败原因 |
|------|-------|------|----------|
| TC-001 | EB-009 | 渲染前运行 check_report.py | evidence 无相关条目，session 原文也未出现 |

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

## 关键约束

- **评估数据来自 subagent 自评**，不自编评估逻辑
- **逐条核对 expected_behaviors**，不跳过不合并
- **按 severity 分级判定**：must→PASS/FAIL，should→PASS/WARN，may→仅观察
- **每条判定必须有证据引用**（`源:定位`），无引用不出现在报告里
- **交叉验证抽查**每用例 2-3 条证据，检测自评偏差
- **SKIP 的用例不做评估**

## 参考文件

本 skill 依赖以下上游文件：
- `test-cases.json` — 测试用例定义（来自 skill-test-designer）
- `run-results/<timestamp>/summary.json` — 运行清单（来自 skill-test-runner）
- `run-results/<timestamp>/TC-xxx-session.md` — subagent 执行 session（来自 skill-test-runner）
- `run-results/<timestamp>/TC-xxx-eval/evidence.json` — subagent 自评证据（subagent 内部 skill-evaluator 产出）
- `run-results/<timestamp>/TC-xxx-eval/findings.json` — subagent 自评发现（subagent 内部 skill-evaluator 产出）

## 错误处理

- **summary.json 不存在**：报告"运行清单缺失"，终止。
- **某用例 eval_dir 下无 evidence.json**：该用例标记为 `MISSING_EVAL`，跳过评估，记录在报告中。
- **expected_behaviors 格式异常**（如缺少 severity 字段）：缺 severity 的默认按 `must` 处理，并在报告中注明。

## 何时不用本 skill

- 设计测试用例 → 用 skill-test-designer
- 运行测试用例 → 用 skill-test-runner
- 直接评估 skill 质量（不经过测试用例） → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
