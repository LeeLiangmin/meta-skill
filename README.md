# meta-skill

元 skill 集合 —— 用于理解、评估、测试 skill 本身的 skill。

## Skill 一览

### 理解与评估

| Skill | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **skill-digest** | 读取一个 skill，产出给人看的理解简报。把隐含的显性化——它要做什么、为什么、流程、验收标准、关键观察点和缺口 | 一个 skill 的 SKILL.md | 理解简报（markdown） |
| **skill-evaluator** | 评估/审计一个 skill，基于事实产出测试报告。每条结论必有证据支撑，区分 observed / inferred / unverified | skill + 执行 session（可选） | 评估报告（report.md） |

### 自动化测试

| Skill | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **skill-test-designer** | 从 skill 中提取可测试行为，设计结构化测试用例（场景 prompt + 预期行为清单） | 被测 skill | `test-cases.json` |
| **skill-test-runner** | 将测试用例并行派发给独立 subagent 执行，收集所有输出 | `test-cases.json` | `run-results/<timestamp>/` |
| **skill-test-judge** | 编排 skill-evaluator 评估每个场景的执行效果，逐条核对预期行为，产出判决报告 | `test-cases.json` + `run-results/` | `report.md` |

## 自动化测试流水线

```
skill-test-designer          skill-test-runner              skill-test-judge
┌─────────────────┐         ┌─────────────────┐          ┌─────────────────┐
│ 读取被测 skill   │────────>│ 读取 test-cases │─────────>│ 读取 test-cases │
│ 分析可测行为     │         │ 每个场景 spawn   │          │ 读取 run-results│
│ 设计场景+期望    │         │   一个 subagent  │          │ 编排 evaluator  │
│                 │         │ 收集所有输出     │          │ 逐条比对检查点   │
└────────┬────────┘         └────────┬────────┘          └────────┬────────┘
         │                           │                            │
         v                           v                            v
  test-cases.json              run-results/                   report.md
```

所有产物放在被测 skill 同级的 `<skill-name>-tests/` 目录下。

### 使用示例

```bash
# 以 skill-digest 为被测 skill，跑完整流水线：

1. 加载 skill-test-designer，为 skill-digest 设计测试用例
   → 产出 .opencode/skills/skill-digest-tests/test-cases.json

2. 加载 skill-test-runner，执行测试用例
   → 产出 skill-digest-tests/run-results/<timestamp>/

3. 加载 skill-test-judge，评判执行结果
   → 产出 skill-digest-tests/report.md
```

### 测试用例格式

每条测试用例包含：场景 prompt（直接喂给 subagent）、严重度分级（must/should/may）、场景类型（normal/pressure/control/exploratory）。预期行为逐条可客观验证，供 judge 自动化比对。

### Skill 之间的关系

```
skill-digest ──→ 理解 skill（静态、不做评判）
skill-evaluator ──→ 评估 skill 执行效果（证据驱动）
                  ↑
                  │ 作为评估引擎
                  │
skill-test-designer → skill-test-runner → skill-test-judge
     设计测试              执行测试            评判结果
```

- `skill-test-judge` 的核心评估引擎是 `skill-evaluator`，不做替代，做编排
- `skill-test-designer` 可选调用 `skill-digest` 快速理解被测 skill
- 创建/修改 skill 本身使用 `skill-creator`
