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

### 3. 并行 spawn 独立 subagent

对同一轮次内所有独立场景，使用 `actor` 工具以 `action=spawn` **同时**派发 subagent：

```
actor({ operation: { action: "spawn", subagent_type: "<用例指定的类型>",
  description: "TC-xxx: <用例名称>",
  prompt: "<用例 prompt>" } })
```

**prompt 必须原封不动使用用例中的 prompt 字段**，不添加解释、不删减内容。

**prompt 预装 skill 指令**：子 agent 加载了被测 skill 才能执行测试。用例 prompt 中应包含加载 target_skill 的指令（test-cases.json 生成时已嵌入）。如果 prompt 中未显式要求加载，在 prompt 末尾追加：

```
在开始前，请先加载被测 skill：<target_skill>
```

### 4. wait 收集所有 subagent 输出

对每个 spawn 出的 actor_id 使用 `actor({ operation: { action: "wait", actor_id: "<id>", timeout_ms: 600000 } })` 阻塞等待完成（默认超时 10 分钟）。

**捕获完整执行 session**：subagent 的 `actor_result` 包含完整对话（所有 turn 的文本和 tool_call）。直接用于写输出文件，不做截断、摘要或改写。

**session 完整性要求**（缺一不可）：
- 必须包含 subagent 从 spawn 到完成的**全部 turn**，不得省略中间任何一步
- 每个 tool_call 的**名称和输入参数**必须可见
- 每个 tool 调用的**返回结果**必须可见（即使失败/超时）
- subagent 的**思考过程**（如有 reasoning/thinking）必须保留
- **时间顺序**保持原样，不重排、不分组

judge 依赖完整体面的 session 才能用 skill-evaluator 做证据型评估——截断或摘要会直接导致评估维度不可评。

### 5. 写入 session 文件

创建输出目录：

```
run-results/<YYYYMMDD-HHMMSS>/
```

对每个用例写入 **session 文件**（供 judge 和 skill-evaluator 使用）：

```
TC-<id>-session.md
```

Session 文件必须以 **JSONL 格式**（首选）或结构化 markdown（备选）记录完整执行过程。优先产出 `.jsonl`；若 actor 工具只提供纯文本输出，降级为 `.md` 但在 summary.json 的 `session_format` 中如实标注。

**JSONL 格式**（首选，每行一条事件）：

```jsonl
{"turn":1,"timestamp":"2026-06-17T08:50:41Z","type":"user_prompt","content":"<发给 subagent 的 prompt 原文>"}
{"turn":2,"timestamp":"2026-06-17T08:50:45Z","type":"tool_call","tool":"read","input":{"filePath":"..."}}
{"turn":2,"timestamp":"2026-06-17T08:50:46Z","type":"tool_result","tool":"read","output":"<读取结果>"}
{"turn":3,"timestamp":"2026-06-17T08:50:50Z","type":"assistant_text","content":"<文本回复>"}
{"turn":3,"timestamp":"2026-06-17T08:50:52Z","type":"tool_call","tool":"write","input":{"filePath":"...","content":"..."}}
{"turn":3,"timestamp":"2026-06-17T08:50:54Z","type":"tool_result","tool":"write","output":"Wrote file successfully."}
{"turn":4,"timestamp":"2026-06-17T08:51:00Z","type":"assistant_text","content":"<最终回复>"}
{"turn":4,"timestamp":"2026-06-17T08:51:00Z","type":"session_end","status":"success"}
```

`type` 取值：`user_prompt` / `assistant_text` / `tool_call` / `tool_result` / `session_end`

**Markdown 备选格式**（当 actor 工具仅输出纯文本时）：

```markdown
# <用例 ID>: <用例名称>
**Target Skill**: <target_skill>
**Subagent Type**: <subagent_type>
**Scenario Type**: <scenario_type>
**Spawned At**: <ISO 8601>
**Completed At**: <ISO 8601>
**Status**: <subagent 返回的 status>

## 完整执行 Session

<subagent actor_result 原文，不做任何修改、截断或摘要>
```

无论哪种格式，**必须保留 subagent 的全部 tool_call 及其输入输出**。judge 通过 skill-evaluator 评估时需要从 session 中提取每条 tool_call 作为原子证据。

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
      "output_file": "TC-001-session.jsonl",
      "started_at": "<ISO 8601>",
      "completed_at": "<ISO 8601>"
    }
  ]
}
```

`status` 取值：
- `success` — subagent 正常完成（包括执行中遇到预期内的缺失资源等非致命情况）
- `failed` — subagent 明确返回 failure
- `timeout` — wait 超时（默认 10 分钟）
- `error` — spawn 失败或 subagent 异常终止
- `skipped` — 所依赖的上游用例失败导致未执行

## 输出目录结构

```
run-results/
└── <YYYYMMDD-HHMMSS>/
    ├── summary.json
    ├── TC-001-session.jsonl
    ├── TC-002-session.md       ← 备选格式（当无法产出 JSONL 时）
    └── ...
```

每次运行创建新的时间戳目录，不覆盖历史结果。

## 关键约束

- **每个场景独立 subagent。** 永远不要在一个 subagent 里顺序执行多个测试用例。一个 subagent = 一个测试用例。
- **prompt 原样传递。** 用例中的 prompt 字段原封不动发给 subagent，不增不减不改写。
- **完整 session 导出。** session 文件必须包含 subagent 的完整执行过程——所有 turn、所有 tool_call 及其输入输出。不做摘要、不截断、不省略中间步骤。judge 通过 skill-evaluator 评估时，每个 tool_call 都是一条潜在证据。
- **并行独立场景。** 无依赖的用例必须并行 spawn（同一轮次内同时发出多个 spawn），不得串行执行。
- **有依赖则串行。** 标记了 `depends_on` 的用例在依赖完成后才 spawn。
- **不评判结果。** runner 只执行和收集，不判断通过/失败。评判是 skill-test-judge 的职责。

## 错误处理

- **spawn 失败**：该用例 status 记为 `error`，写入 `TC-<id>-session.md` 中说明 spawn 失败原因。不阻塞其他用例。
- **wait 超时**：该用例 status 记为 `timeout`，写入 session 文件中说明超时，保留已收到的部分输出。不阻塞其他用例。
- **test-cases.json 不存在**：报告文件不存在，终止执行。
- **test-cases.json 格式不合法**：报告具体格式错误（缺失字段、类型错误），终止执行。

## 何时不用本 skill

- 设计测试用例 → 用 skill-test-designer
- 评判测试执行结果 → 用 skill-test-judge
- 评估 skill 质量 → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
