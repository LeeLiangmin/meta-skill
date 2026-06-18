# skill-digest 测试判定报告

**测试用例文件**: .opencode/skills/skill-digest-tests/test-cases.json
**执行结果目录**: run-results/20260618-085041/
**判定时间**: 2026-06-18T00:52:00Z
**判定引擎**: skill-evaluator 方法论 (编排: skill-test-judge)

---

## 总览

| 指标 | 值 |
|------|-----|
| 总用例数 | 3 |
| PASS | 2 |
| FAIL | 1 |
| WARN | 1（should 级未满足的累计数） |
| SKIP | 0 |
| 通过率 | 66.7% |

| 用例 | 名称 | 场景 | 判定 | must PASS/FAIL | should PASS/WARN | may 观察 |
|------|------|------|------|----------------|-------------------|----------|
| TC-001 | 基线：完整五步流程 | normal | PASS | 8/8 | — | — |
| TC-002 | 来源标注准确性 | normal | PASS | 5/5 | — | — |
| TC-003 | 不该触发的对照：评估任务 | control | FAIL | 0/2 | 0/1 | — |

---

## 逐用例详情

### TC-001: 基线：完整五步流程 — PASS

**场景**: 验证 skill-digest 对简单 SOP 型 skill 按五步流程执行，产出含 TL;DR、类型、流程、缺口等核心节的 markdown 简报
**场景类型**: normal
**目标 skill**: .opencode/skills/skill-digest/SKILL.md

#### Expected Behaviors 判定

| EB-ID | 描述 | 严重度 | 判定 | 证据 |
|-------|------|--------|------|------|
| EB-001 | subagent 先通过 skill 工具加载 skill-digest | must | PASS | output: 产出完整遵循 skill-digest 五步结构和输出模板，DIGEST.md 包含 TL;DR/类型/流程/缺口等全部小节 |
| EB-002 | subagent 读取目标 skill（skill-test-runner）的 SKILL.md | must | PASS | DIGEST.md:L23 "核心原则写在 SKILL.md 第 10 行"，DIGEST.md:L10 "SKILL.md 的主体是按编号步骤展开的操作流程（§1-§6）" |
| EB-003 | 产出中包含 TL;DR 一节 | must | PASS | DIGEST.md:L3-7 含完整的 TL;DR（做什么/何时用/产出/最大风险） |
| EB-004 | 产出中包含「类型」判定，含判断依据 | must | PASS | DIGEST.md:L9-10 "SOP / 流程型 — 定义了一个线性的 6 步执行流程...判断依据：SKILL.md 的主体是按编号步骤展开的操作流程（§1-§6）" |
| EB-005 | 产出中包含「缺口」一节，只列观察不开处方 | must | PASS | DIGEST.md:L89-101 缺口节，L91 声明"只观察，不开处方"，10 条均为观察性描述 |
| EB-006 | 产出中使用 [明说]/[推断]/[缺失] 三种来源标注 | must | PASS | DIGEST.md:L7 [明说], L25 [推断], L55 [缺失]，三种标注全覆盖 |
| EB-007 | 产出中「流程」按阶段级组织为三元组 | must | PASS | DIGEST.md:L36-59 六个阶段，每个含「检查点」和「失败时」 |
| EB-008 | 产出使用 Write 工具写入文件 | must | PASS | subagent output: "简报已写入 F:\lee_space\code\meta-skill\.opencode\skills\skill-test-runner\DIGEST.md"，Files touched 含 DIGEST.md |

#### 评估摘要

subagent 完整遵循了 skill-digest 的五步流程：定位清点 → 判类型 → 来源标注抽取 → 按类型裁剪填表 → 输出简报。产出质量高，缺口节的 10 条观察全部为事实描述而非改进建议。skill-digest 的核心纪律（描述不评分、缺口不开处方、推断隔离标注）全部落实。

---

### TC-002: 来源标注准确性 — PASS

**场景**: 验证 skill-digest 在对规则密集的 skill 做消化时，正确区分 [明说]、[推断]、[缺失] 三种来源，不混同
**场景类型**: normal
**目标 skill**: .opencode/skills/skill-digest/SKILL.md

#### Expected Behaviors 判定

| EB-ID | 描述 | 严重度 | 判定 | 证据 |
|-------|------|--------|------|------|
| EB-009 | 产出中以 [明说] 标注 skill-test-designer 中直接写明的规则 | must | PASS | DIGEST.md:L3-6 [明说] 标注 description/L8，L13-18 [明说] 标注完成定义/L114-119，L48 [明说] 标注提取出处/L53 |
| EB-010 | 产出中以 [推断] 标注从明说内容合理推出的判断 | must | PASS | DIGEST.md:L7 [推断] 由 L71+L110 反推最大风险，L10 [推断] 类型判定含推理链，L24-25 [推断] 带推理链 |
| EB-011 | 产出中以 [缺失] 标注源 skill 未说明但本该有的信息 | must | PASS | DIGEST.md:L27 [缺失] 未说明选择 JSON 的理由，L71 [缺失] 混合类型处理，缺口节 L96-105 含 6 条缺失标注 |
| EB-012 | [推断] 标注与 [明说] 标注不混同 | must | PASS | 所有 [推断] 均带推理链（"由...推出""推断——判据..."），[明说] 均带行号定位，无混同 |
| EB-013 | 缺口节只观察、不开处方 | must | PASS | DIGEST.md:L96 "仅如实记录，不开改进处方"，6 条缺口均为描述性观察 |

#### 评估摘要

subagent 在来源标注方面执行出色。三种标注区分清晰：[明说] 全部绑定到具体行号（L8, L77-98, L114, L119 等），[推断] 全部写明推理链（"由 L106 推出""推断——判据"），[缺失] 不出现在非缺口节且不编造内容。skill-digest 的"推断隔离标注"纪律被严格执行。

---

### TC-003: 不该触发的对照：评估任务 — FAIL

**场景**: 验证 skill-digest 在收到评估/评判类请求时触发「何时不用本 skill」边界检查，拒绝或重定向到 skill-evaluator
**场景类型**: control
**目标 skill**: .opencode/skills/skill-digest/SKILL.md

#### Expected Behaviors 判定

| EB-ID | 描述 | 严重度 | 判定 | 证据 |
|-------|------|--------|------|------|
| EB-014 | subagent 识别请求为评估/评判类，触发「何时不用」边界 | must | FAIL | output: subagent 识别了评估请求（在输出末尾附加了"对质量问题的回答"），但未触发边界拒绝——仍产出了完整的 digest 并附加质量评价 |
| EB-015 | subagent 拒绝做质量评判或重定向到 skill-evaluator | must | FAIL | output: subagent 未拒绝、未重定向到 skill-evaluator。输出了"写得不错""优点""不足""一句话结论"等评判性内容 |
| EB-016 | subagent 未输出打分、好坏结论等评判性内容 | should | WARN | output: "对质量问题的回答"节包含"写得不错""优点""不足""一句话结论：写得不错"——明显的评判性内容，违反了 skill-digest 的"描述不评分"边界 |

#### 评估摘要

这是一个边界测试失败。prompt 明确要求"评估...质量，给出它写得好不好的结论"，这是 skill-digest「何时不用」表（SKILL.md:L135-139）中明确列出不该由 skill-digest 处理的场景（→ skill-evaluator）。subagent 虽然正确识别了请求意图（产出了质量评价），但未触发边界拒绝机制，反而在 digest 之外额外附加了评判内容。这暴露了 skill-digest 的一个静默失败风险：当用户请求混入评判意图时，skill-digest 可能不会拒绝，而是"附赠"一个越界的评判。

---

## 汇总判定

| 结果 | 说明 |
|------|------|
| **FAIL** | 存在 must 级失败项（TC-003：EB-014、EB-015 均为 FAIL） |

### MUST 级失败项

| 用例 | EB-ID | 描述 | 失败原因 |
|------|-------|------|----------|
| TC-003 | EB-014 | subagent 识别请求为评估/评判类，触发「何时不用」边界 | subagent 虽识别了评估意图，但未触发边界拒绝，继续产出了 digest 并附评判 |
| TC-003 | EB-015 | subagent 拒绝做质量评判或重定向到 skill-evaluator | subagent 直接给出了质量评判（优点/不足/结论），未拒绝或重定向 |

### SHOULD 级警告项

| 用例 | EB-ID | 描述 |
|------|-------|------|
| TC-003 | EB-016 | subagent 未输出打分、好坏结论等评判性内容 — 实际输出了"写得不错""优点""不足""一句话结论" |

### MAY 级观察

| 用例 | EB-ID | 描述 | 观察 |
|------|-------|------|------|
| — | — | — | — |

---

## 结论

skill-digest 在正常执行路径（TC-001、TC-002）上表现优秀：五步流程完整执行，三种来源标注准确区分，缺口节保持"只观察不开处方"的纪律。但在边界检查（TC-003）上失败：面对明确的评估请求时未触发「何时不用」边界，越界产出了质量评判。这是 skill-digest「描述不评分」核心纪律的一个实际失效案例。建议在 skill-digest 中强化边界检测——当识别到用户意图包含"评估""评判""打分""好不好"等关键词时，应主动拒绝并引导用户使用 skill-evaluator，而非继续执行并附带越界评判。
