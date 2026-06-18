# Findings.json Schema

本文件定义 `findings.json` 的完整数据结构，与 `evidence.json`（见 `evidence-ledger.md`）共同构成评估报告的数据层。

## 顶层结构

```json
{
  "target_skill": "被测 skill 的名字或路径",
  "evaluated_at": "2026-06-17",
  "findings": [
    {
      "id": "F1",
      "dimension": "instruction_correctness",
      "severity": "high",
      "status": "observed",
      "statement": "skill 第 40 行要求使用已废弃的 API",
      "evidence_ids": ["E1", "E2"],
      "reasoning": "",
      "verification": {
        "performed": true,
        "method": "subagent",
        "result": "confirmed",
        "evidence_ids": ["E3"]
      }
    }
  ],
  "verdict": {
    "rating": "pass",
    "summary": "总评一段话",
    "summary_finding_ids": ["F1", "F2"]
  },
  "gaps": [
    {
      "id": "G1",
      "description": "缺少执行 session，执行保真度无法评估",
      "reason": "用户未提供运行记录"
    }
  ],
  "recommendations": [
    {
      "finding_id": "F1",
      "text": "将废弃 API 替换为新版本"
    }
  ],
  "missing_sources": [
    "session（用户未提供）"
  ]
}
```

## 字段说明

### `findings[]` — 发现列表

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 唯一标识，建议用 `F1`, `F2` 格式 |
| `dimension` | string | 是 | 评估维度，必须是以下之一：`instruction_correctness`, `consistency_completeness`, `triggering`, `execution_fidelity`, `outcome_quality`, `efficiency`, `safety_intent` |
| `severity` | string | 是 | 严重度：`high`（影响可用性）/ `medium`（值得注意）/ `low`（轻微） |
| `status` | string | 是 | 结论状态：`observed`（直接观察到的事实）/ `inferred`（经推理得出） |
| `statement` | string | 是 | 发现的具体陈述，一句话概括 |
| `evidence_ids` | string[] | 是 | 支撑本发现的所有证据 ID，至少一个，必须在 `evidence.json` 中存在 |
| `reasoning` | string | 条件必填 | 当 `status=inferred` 时必须填写，写明推理链条 |
| `verification` | object | 条件必填 | 当 `severity=high` 时必须填写 |

### `verification` 对象

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `performed` | boolean | 是 | 是否执行了校验 |
| `method` | string | 是 | 校验方法：`subagent`（独立 subagent）/ `fresh_eyes`（新视角复核） |
| `result` | string | 是 | 校验结果：`confirmed`（支持）/ `refuted`（推翻）/ `inconclusive`（无法判定） |
| `evidence_ids` | string[] | 否 | 校验过程中产生的新证据 ID |

**注意**：`result=refuted` 的发现不应保留在 findings 中，应删除或改写。

### `verdict` — 总评

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `rating` | string | 是 | 总评等级：`pass`（通过）/ `pass_with_issues`（有问题但可用）/ `fail`（不通过）/ `inconclusive`（证据不足） |
| `summary` | string | 是 | 总评的简要说明 |
| `summary_finding_ids` | string[] | 条件必填 | 当 `rating` 为 `pass_with_issues`, `fail`, `inconclusive` 时，必须列出支撑该结论的发现 ID |

### `gaps[]` — 盲区与局限

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 否 | 可选标识，如 `G1` |
| `description` | string | 是 | 盲区的具体描述 |
| `reason` | string | 否 | 为何成为盲区（如"缺少 session"） |

### `recommendations[]` — 改进建议

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `finding_id` | string | 否 | 针对哪条发现提出的建议 |
| `text` | string | 是 | 建议内容 |

也可简化为字符串数组（`["建议1", "建议2"]`），但推荐使用对象形式以便追溯。

### `missing_sources` — 缺失的来源

字符串数组，记录请求过但未能获得的来源。用于报告"来源"一节。例如：
```json
["session（用户未提供运行记录）", "external（官方文档链接失效）"]
```

## 与 check_report.py 的校验规则对应

`scripts/check_report.py` 会强制检查以下规则：

1. `findings[].id` 必须唯一
2. `dimension` 必须在预定义集合中
3. `severity` 必须是 `high`/`medium`/`low`
4. `status` 必须是 `observed`/`inferred`
5. `statement` 不能为空
6. `evidence_ids` 不能为空，且每个 ID 必须在 `evidence.json` 中存在
7. `status=inferred` 时 `reasoning` 不能为空
8. `severity=high` 时 `verification.performed` 必须为 `true`，且 `method` 不能为 `none`
9. `verification.result=refuted` 时会被报错（应删除该发现）
10. `verdict.rating` 必须在预定义集合中
11. `verdict.summary_finding_ids` 中的每个 ID 必须存在于 findings 中
12. `rating` 为 `pass_with_issues` 或 `fail` 时，建议（非强制）提供 `summary_finding_ids`

## 填写技巧

- **一条发现只陈述一个事实或结论**。不要把多个问题混在一条发现里。
- **evidence_ids 要精确**。不要引用无关证据，也不要遗漏关键证据。
- **高严重度发现必须校验**。这是防止确认偏误的关键机制。
- **盲区要诚实写出**。隐藏盲区等于制造虚假的全面感。
- **改进建议要可执行**。避免泛泛而谈如"需要改进"，应具体如"将 X 替换为 Y"。
