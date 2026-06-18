---
name: skill-test-runner
description: 使用本 skill 将一个 test-cases.json 中的测试用例批量分派给独立 subagent 执行，收集全部输出并生成运行清单。当用户需要按 test-cases.json 跑测试、批量验证一个 skill 的行为、或需要可追溯的自动化测试执行记录时使用本 skill。触发语包括"执行这些测试用例""跑 test-cases.json""运行 skill 测试"。
---

# Skill Test Runner

本 skill 的唯一目标：读入 `test-cases.json`，将每个测试用例分派给独立 subagent 执行，收集完整输出，产出一份机器可读的运行清单和每用例的独立输出文件。它不做评判——那是 skill-test-judge 的事。

核心原则：**每个测试场景必须独立 subagent 执行，避免状态交叉污染。** 同一个 subagent 连续执行多个测试用例 = 上下文残留 = 结果不可信。

## 流程

### 1. 读取并确认 test-cases.json

用 `Read` 工具读入文件。确认顶层字段：`skill_name`、`test_cases`（数组）。每条用例必须有 `id`、`prompt`、`subagent_type`。

**审核状态检查**：检查 test-cases.json 中是否存在 `reviewed_at` 字段。若缺失，说明测试用例尚未经过人工审核——**不可继续执行**。此时：

1. 提醒用户："该 test-cases.json 尚未经过人工审核（缺少 reviewed_at 字段）。请先用 skill-test-designer 生成并审核测试用例。"
2. 若用户坚持要执行（如开发调试中），使用 `question` 工具确认：
   - header: `Skip Review`
   - question: `test-cases.json 未经人工审核。确定要跳过审核直接执行吗？`
   - options:
     - label: `Skip review, execute`, description: `跳过审核，直接执行（仅调试用）`
     - label: `Cancel`, description: `取消，先去审核测试用例`

若用户选 `Cancel`，终止执行。选 `Skip review, execute` 方可继续。

### 2. 识别依赖关系

扫描所有用例的 `depends_on` 字段（若存在）。没有 `depends_on` 的 = 独立场景，可并行执行。有 `depends_on` 的 = 必须在依赖的用例完成后才执行。给每条用例标上执行轮次。

**依赖失败处理**：若被依赖的用例执行失败（status=failed/timeout/error），其所有直接和间接下游用例标记为 `skipped`，不执行。

### 3. 构造 subagent prompt 并 spawn

对同一轮次内所有独立场景，使用 `actor` 工具以 `action=spawn` **同时**派发 subagent。

**prompt 构造规则**：以用例的 `prompt` 字段为基础，末尾追加自评指令（见下方模板），原样发给 subagent，不增不减不改写。

**自评指令追加**（每条用例必须追加）：

```
---

完成上述任务后，请立即执行以下自评步骤：

1. 使用 `skill` 工具加载 **skill-evaluator**。
2. 以你**本次完整的执行过程**为 session（你拥有全部上下文——所有 tool_call、输入输出、思考过程都在你眼前），评估你是否按被测 skill <target_skill> 的要求执行了。
3. 产出 evidence.json 和 findings.json，写入 <output_dir>/<case_id>-eval/ 目录。
4. 你只需产出 evidence.json 和 findings.json，不需要渲染 report.md。

注意：你在做自评时，skill-evaluator 能看到你本次执行的所有消息（包括所有 tool_call）。请充分利用这一优势，精确抽取每一条 tool_call 作为原子证据。
```

其中 `<target_skill>` 替换为用例的 `target_skill` 字段，`<output_dir>` 替换为 `run-results/<timestamp>/`，`<case_id>` 替换为用例的 `id`。

**prompt 预装 skill 指令**：如果用例的原始 prompt 中未显式要求加载被测 target_skill，在 prompt 开头追加：

```
在开始前，请先加载被测 skill：<target_skill>
```

**spawn 调用**：

```
actor({ operation: { action: "spawn", subagent_type: "<用例指定的类型>",
  description: "TC-xxx: <用例名称>",
  prompt: "<完整 prompt（原始 + 自评指令）>" } })
```

### 4. wait 收集所有 subagent 输出

对每个 spawn 出的 actor_id 使用 `actor({ operation: { action: "wait", actor_id: "<id>", timeout_ms: 600000 } })` 阻塞等待完成（默认超时 10 分钟）。

subagent 的 `actor_result` 将包含：执行过程 + 自评结果（evidence.json + findings.json 的内容或路径）。

### 5. 写入输出文件

创建输出目录：

```
run-results/<YYYYMMDD-HHMMSS>/
```

对每个用例写入 session 文件：

```
TC-<id>-session.md
```

内容格式：

```markdown
# <用例 ID>: <用例名称>

**Target Skill**: <target_skill>
**Subagent Type**: <subagent_type>
**Scenario Type**: <scenario_type>
**Actor ID**: <actor_id>
**Status**: <subagent 返回的 status>

## 完整执行 Session（含自评）

<actor_result 原文，不做任何修改、截断或摘要>
```

subagent 的自评产物（evidence.json 和 findings.json）如果已写入文件系统，记入 summary.json；如果只在 actor_result 文本中，由 judge 提取。

### 6. 写入 summary.json

在同一时间戳目录下写入 `summary.json`，schema：

```json
{
  "skill_name": "<被测 skill 名称>",
  "skill_path": "<被测 skill 路径>",
  "test_cases_file": "<test-cases.json 的路径>",
  "executed_at": "<ISO 8601 时间戳>",
  "total": <用例总数>,
  "results": [
    {
      "id": "TC-001",
      "name": "<用例名称>",
      "status": "success | failed | timeout | error",
      "subagent_type": "general",
      "scenario_type": "normal",
      "target_skill": "<target_skill 路径>",
      "actor_id": "<subagent 的 actor_id>",
      "output_file": "TC-001-session.md",
      "eval_dir": "TC-001-eval/",
      "started_at": "<ISO 8601>",
      "completed_at": "<ISO 8601>"
    }
  ]
}
```

`status` 取值：
- `success` — subagent 正常完成（含自评）
- `failed` — subagent 明确返回 failure
- `timeout` — wait 超时（默认 10 分钟）
- `error` — spawn 失败或 subagent 异常终止
- `skipped` — 所依赖的上游用例失败导致未执行

## 输出目录结构

```
run-results/
└── <YYYYMMDD-HHMMSS>/
    ├── summary.json
    ├── TC-001-session.md
    ├── TC-001-eval/
    │   ├── evidence.json      ← subagent 自评产出
    │   └── findings.json
    ├── TC-002-session.md
    └── ...
```

每次运行创建新的时间戳目录，不覆盖历史结果。

## 关键约束

- **每个场景独立 subagent。** 一个 subagent = 一个测试用例。不可在一个 subagent 里跑多个用例。
- **prompt 追加自评指令。** 每条用例的 prompt 末尾必须追加自评指令，要求 subagent 用 skill-evaluator 自评。
- **session 保存原文。** actor_result 原文写入 session 文件，不做截断或摘要。
- **并行独立场景。** 无依赖的用例必须并行 spawn（同一轮次内同时发出多个 spawn）。
- **有依赖则串行。** 标记了 `depends_on` 的用例在依赖完成后才 spawn。
- **不评判结果。** runner 只执行和收集，不判断通过/失败。评判是 skill-test-judge 的职责。

## 自评机制说明

runner 无法访问 subagent 内部的 tool_call 明细（actor_result 只含 subagent 的最终输出文本），因此不能由 runner 事后做评估。取而代之的是：subagent 在完成测试任务后**当场**加载 skill-evaluator 对自己的执行过程做自评——evaluator 在 subagent 内部运行，天然可访问其全部 tool_call 和 reasoning 上下文。

自评产出的 evidence.json 和 findings.json 由 judge 用于后续的 checklist 比对和交叉验证。

## 错误处理

- **spawn 失败**：该用例 status 记为 `error`，写入 `TC-<id>-session.md` 中说明原因。不阻塞其他用例。
- **wait 超时**：该用例 status 记为 `timeout`，写入 session 文件中说明超时。不阻塞其他用例。
- **test-cases.json 不存在**：报告文件不存在，终止执行。
- **test-cases.json 格式不合法**：报告具体格式错误，终止执行。

## 何时不用本 skill

- 设计测试用例 → 用 skill-test-designer
- 评判测试执行结果 → 用 skill-test-judge
- 评估 skill 质量 → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
