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

**收集完整对话**：subagent 的 `actor_result` 字段即为完整输出（含所有 tool_call 和文本）。直接用于写输出文件，不做截断或摘要。

### 5. 写入输出文件

创建输出目录：

```
run-results/<YYYYMMDD-HHMMSS>/
```

对每个用例写入：

```
TC-<id>-output.md
```

内容格式：

```markdown
# <用例 ID>: <用例名称>

**Status**: <subagent 返回的 status>
**Target Skill**: <target_skill>
**Subagent Type**: <subagent_type>
**Scenario Type**: <scenario_type>

## 完整 Subagent 输出

<subagent 的 actor_result 原文，不做任何修改>
```

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
      "output_file": "TC-001-output.md",
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
    ├── TC-001-output.md
    ├── TC-002-output.md
    └── ...
```

每次运行创建新的时间戳目录，不覆盖历史结果。

## 关键约束

- **每个场景独立 subagent。** 永远不要在一个 subagent 里顺序执行多个测试用例。一个 subagent = 一个测试用例。
- **prompt 原样传递。** 用例中的 prompt 字段原封不动发给 subagent，不增不减不改写。
- **完整对话保留。** 输出文件记录 subagent 的完整原始输出（含 tool_call ），不做摘要、不截断。judge 需要完整上下文才能判断。
- **并行独立场景。** 无依赖的用例必须并行 spawn（同一轮次内同时发出多个 spawn），不得串行执行。
- **有依赖则串行。** 标记了 `depends_on` 的用例在依赖完成后才 spawn。
- **不评判结果。** runner 只执行和收集，不判断通过/失败。评判是 skill-test-judge 的职责。

## 错误处理

- **spawn 失败**：该用例 status 记为 `error`，写入 `TC-<id>-output.md` 中说明 spawn 失败原因。不阻塞其他用例。
- **wait 超时**：该用例 status 记为 `timeout`，写入输出文件中说明超时。不阻塞其他用例。
- **test-cases.json 不存在**：报告文件不存在，终止执行。
- **test-cases.json 格式不合法**：报告具体格式错误（缺失字段、类型错误），终止执行。

## 何时不用本 skill

- 设计测试用例 → 用 skill-test-designer
- 评判测试执行结果 → 用 skill-test-judge
- 评估 skill 质量 → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
