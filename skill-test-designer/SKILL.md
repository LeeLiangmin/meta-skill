---
name: skill-test-designer
description: 为一个已有的 skill 自动设计测试用例——提取可测试行为、构造场景 prompt、定义结构化预期结果。当你需要系统化地验证一个 skill 是否按预期工作时使用本 skill。触发场景：(1) 为新 skill 设计测试用例，(2) 为已有 skill 补充测试覆盖，(3) 构建 skill 测试管道中的第一步。
---

# Skill Test Designer

本 skill 的唯一目标：读入一个被测 skill，输出一份机器可执行的 `test-cases.json`，供 skill-test-runner 和 skill-test-judge 使用。

核心原则：**skill 不是代码，但测试用例要像代码测试一样可重复、可判断、可自动化。** 这意味着输出必须是结构化 JSON，每个用例必须带完整的 subagent prompt 和明确的预期行为，不可依赖人工解读。

## 被测 skill 类型判定

读取被测 skill 后，先判类型（判断会影响场景设计侧重点）：

| 类型 | 特征 | 测试重点 |
|------|------|----------|
| SOP/流程型 | 按步骤执行、有验收门控 | 步骤是否按序执行、检查点是否全部通过 |
| 工具转换型 | 给定输入产出特定输出 | 输入输出契约、边界情况、格式正确性 |
| 顾问/启发式型 | 给原则判断、无固定流程 | 原则是否被遵循、何时不用、反目标是否触发 |

## 可测试行为提取策略

从被测 skill 中提取行为，映射到测试级别：

| 提取来源 | 对应的测试级别 | 场景类型 |
|----------|---------------|----------|
| skill 的硬规矩（"必须""务必""否则即返工"） | `must` — 不通过则 skill 失效 | 正常执行场景 |
| skill 的流程/步骤（每一步做什么、怎么确认完成） | `must` — 步骤缺失或乱序即失败 | 正常执行场景 |
| skill 的反目标/常见错误（"不要""禁止""常见的坑"） | `should` — 应避免，出现了算问题 | 压力/边界场景 |
| skill 的"何时不用本 skill"（边界判断） | `should` — 该拒绝的场景 | 不该触发的对照场景 |
| skill 的缺口/未说明之处（明写"TODO""未覆盖"或推断的盲区） | `may` — 可探索但非强制 | 探索性场景 |

## 流程

### 1. 定位并遍历被测 skill

读取被测 skill 的 SKILL.md。**关键：顺着它的引用往下读。** 只读 SKILL.md 抽出来的行为是残的——references/scripts/assets 里常有隐含的硬规矩和边界定义。遍历文件树时设合理深度，不无限展开。

### 2. 判类型

按照上表的分类判类型，据此决定后续场景设计侧重点。

### 3. 提取可测试行为

逐段扫描被测 skill 文本，按提取策略表将每一处可测试行为归类：
- 硬规矩 → `must` + 正常执行场景
- 流程步骤 → `must` + 正常执行场景
- 反目标/常见错误 → `should` + 压力/边界场景
- "何时不用" → `should` + 不该触发的对照场景
- 缺口/盲区 → `may` + 探索性场景

**每一处提取都记下出处**（文件名 + 行号），以便 judge 回溯。

### 4. 设计测试场景并写完整 prompt

为每类行为设计至少一个测试场景。每个场景写一条**完整、自包含的 subagent prompt**——这条 prompt 会原封不动发给 subagent，不能依赖外部上下文（如"见前述""同上"）。prompt 中必须包含被测 skill 的路径引用，使 runner 可直接根据 `target_skill` 确保 subagent 可访问。

场景设计覆盖维度：
- **正常路径**：skill 按预期执行的 happy path
- **压力/边界**：异常输入、缺失资源、模糊指令、故意踩反目标
- **不该触发的对照**：输入不应触发该 skill 的场景

### 5. 定义预期行为

每个测试用例的每一条预期行为，写成一个独立条目：
- `id`：全局唯一 ID，如 `EB-001`
- `description`：可客观判断的行为描述（"subagent 先 read_file 确认 SKILL.md 可读"而非"subagent 工作正常"）
- `severity`：must / should / may

**预期行为必须可被 judge 客观验证**。避免含混词（"较好地""大致""基本"），用可核对的动作和产出描述。

### 6. 产出 test-cases.json

按以下 schema 写入 JSON：

```json
{
  "skill_name": "skill-evaluator",
  "skill_path": ".opencode/skills/skill-evaluator/SKILL.md",
  "generated_at": "<ISO 8601>",
  "test_cases": [
    {
      "id": "TC-001",
      "name": "基线：正常评估流程",
      "description": "验证 skill-evaluator 在获得完整三类来源时按 0-4 步流程执行",
      "target_skill": ".opencode/skills/skill-evaluator/SKILL.md",
      "scenario_type": "normal",
      "prompt": "完整的 subagent 执行指令，自包含、可原封不动发给 subagent",
      "subagent_type": "general",
      "expected_behaviors": [
        { "id": "EB-001", "description": "先 read_file 确认被测 skill 路径可读", "severity": "must" },
        { "id": "EB-002", "description": "建立 evidence.json 证据账本", "severity": "must" }
      ]
    }
  ]
}
```

字段说明：
- `id`：用例唯一 ID，格式 TC-XXX（三位数字，从 001 起）
- `name`：短名称，5-10 个字，描述测什么
- `description`：1-2 句话说明场景和验证目标
- `target_skill`：被测 skill 的路径，runner 用此确保 subagent 可访问
- `scenario_type`：normal（正常路径）/ pressure（压力/边界）/ control（不该触发的对照）/ exploratory（探索性）
- `prompt`：**完整、自包含**的 subagent 指令。必须独立可读、不依赖当前对话上下文
- `subagent_type`：建议的 subagent 类型（explore 或 general）
- `expected_behaviors[].severity`：must / should / may

## 用例设计自检清单

写出 test-cases.json 之前，过一遍：

- [ ] 至少覆盖 must / should / may 三个级别
- [ ] 至少包含 normal 和 pressure 两类 scenario_type
- [ ] 每个 prompt 独立可读，不含"同上""见前文"等引用
- [ ] 每个用例指定了 target_skill 路径
- [ ] 每个用例指定了 subagent_type
- [ ] 每条 expected_behavior 可客观验证，不含含混词
- [ ] 每条 expected_behavior 的 id 全局唯一

## 输出

使用 `Write` 工具将 test-cases.json 写入被测 skill 同级目录下的 `<skill-name>-tests/` 文件夹：

```
.opencode/skills/<skill-name>-tests/
└── test-cases.json
```

完成后报告：生成了多少个测试用例、must/should/may 各多少个、覆盖了哪些 scenario_type。

## 何时不用本 skill

- 创建或编写 skill 本身 → 用 skill-creator
- 评估 skill 质量 → 用 skill-evaluator
- 理解 skill 内容 → 用 skill-digest
- 运行已有测试用例 → 用 skill-test-runner
- 评判测试执行结果 → 用 skill-test-judge
