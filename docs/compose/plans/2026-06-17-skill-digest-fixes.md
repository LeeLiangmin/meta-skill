# skill-digest 改进实现计划

> [!NOTE]
> This document may not reflect the current implementation.
> See the final report for up-to-date state:
> [Final Report](../reports/skill-digest-fixes.md)

> **For agentic workers:** REQUIRED SUB-SKILL: Use compose:subagent (recommended) or compose:execute to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 根据 skill-evaluator 评估报告修复 skill-digest 的 2 个高严重度和 4 个中等问题（F1-F8），改动集中在 `skill_digest/SKILL.md` 单文件。

**Architecture:** 单文件编辑，7 处改动分布在 SKILL.md 不同位置。无新增文件、无依赖变更。改动顺序按在文件中出现位置（自上而下）编排，避免跳跃。

**Tech Stack:** 纯文本 Markdown 编辑

---

## 改动前基线

当前 `skill_digest/SKILL.md` 关键行：

```
L3:   description: ...注意：本 skill 只做中立的描述性理解、不评判质量（要评判/审计→skill-evaluator）...
L14:  - **描述，不评分。** ...
L27:  ### 2. 判类型
L34:  判错类型会导致填出空洞或编造的小节...
L48:  ### 5. 输出前置式简报
L84:  ### 关键观察点
L96:  ### 失败模式 / 反目标
L107: 最后用 `present_files` 把简报交给用户。
```

---

### Task 1: 修复 F8 — 加强 description 触发区分

**Covers:** [F8]

**Files:**
- Modify: `skill_digest/SKILL.md:L3`

- [ ] **Step 1: 修改 description 的尾句，加强触发词区分**

原 L3:
```
注意：本 skill 只做中立的描述性理解、不评判质量（要评判/审计→skill-evaluator），也不创建或修改 skill（→skill-creator）。
```

改为：
```
注意：本 skill 只做中立的描述性理解、不评判质量（要评判/审计→skill-evaluator），也不创建或修改 skill（→skill-creator）。触发词区分："理解/读懂/搞清楚/快速了解"触发本 skill；"测评/评估/审计/测试报告"触发 skill-evaluator。
```

- [ ] **Step 2: 确认改动正确**

Run: `grep "触发词区分" skill_digest/SKILL.md`
Expected: 输出包含该行

- [ ] **Step 3: Commit**

```bash
git add skill_digest/SKILL.md
git commit -m "fix(skill-digest): 加强 description 中与 skill-evaluator 的触发词区分 (F8)"
```

---

### Task 2: 修复 F2 — 添加自类型声明 + 混合型指引

**Covers:** [F2]

**Files:**
- Modify: `skill_digest/SKILL.md:L14-L34`

- [ ] **Step 1: 在三条边界后插入自类型声明**

在 L18（三条边界末尾）和 L20（"另外..."）之间插入新段落：

```
**本 skill 自身的类型：SOP/流程型 + 顾问/启发式型 混合** —— 五步流程是 SOP 骨架，三条边界和类型判定是顾问式原则。执行时按 SOP 型走流程，同时在简报中按需要补充顾问型小节（核心原则）。
```

注意：插入后原 L20 的 `（另外：本 skill 只做静态理解...）` 向下移位。

- [ ] **Step 2: 在类型判断区新增混合型处理指引**

原 L27-L34（第 2 步判类型末尾），在 L34 之后添加：

```
判为混合型时：按主要类型（通常是 SOP 型）走输出结构，同时在核心原则 / 适用不适用等顾问型小节中补充判断原则。不要因为混合就省略任一侧的重要信息。
```

- [ ] **Step 3: 确认改动正确**

Run: `grep "本 skill 自身的类型" skill_digest/SKILL.md && grep "判为混合型" skill_digest/SKILL.md`
Expected: 两行均存在

- [ ] **Step 4: Commit**

```bash
git add skill_digest/SKILL.md
git commit -m "fix(skill-digest): 添加自类型声明和混合型处理指引 (F2)"
```

---

### Task 3: 修复 F4 — 为缺少标注的小节补充类型标签

**Covers:** [F4]

**Files:**
- Modify: `skill_digest/SKILL.md:L84-L97`

- [ ] **Step 1: 为"关键观察点"加标注**

原 L84:
```
## 关键观察点
如果只盯几个地方，盯哪几个——即最容易**静默失败**...
```

改为：
```
## 关键观察点  ← 所有类型适用
如果只盯几个地方，盯哪几个——即最容易**静默失败**...
```

- [ ] **Step 2: 为"失败模式 / 反目标"加标注**

原 L96:
```
## 失败模式 / 反目标
常见的踩坑、明确"不要做"的事。
```

改为：
```
## 失败模式 / 反目标  ← 所有类型适用
常见的踩坑、明确"不要做"的事。
```

- [ ] **Step 3: 确认改动正确**

Run: `grep "← 所有类型适用" skill_digest/SKILL.md`
Expected: 2 行匹配

- [ ] **Step 4: Commit**

```bash
git add skill_digest/SKILL.md
git commit -m "fix(skill-digest): 为关键观察点和失败模式小节补充类型标签 (F4)"
```

---

### Task 4: 修复 F1+F3 — 交付方式改为默认对话展示

**Covers:** [F1, F3]

**Files:**
- Modify: `skill_digest/SKILL.md:L107`

- [ ] **Step 1: 替换 present_files 指令**

原 L107:
```
最后用 `present_files` 把简报交给用户。
```

改为：
```
默认将简报直接在对话中展示给用户；若用户明确要求落盘，则将简报写入 markdown 文件。
```

- [ ] **Step 2: 确认改动正确**

Run: `grep "默认将简报直接在对话中展示" skill_digest/SKILL.md`
Expected: 输出包含该行

- [ ] **Step 3: Commit**

```bash
git add skill_digest/SKILL.md
git commit -m "fix(skill-digest): 交付方式改为默认对话展示，用户要求时落盘 (F1, F3)"
```

---

### Task 5: 修复 F5 — 加强"描述不评分"的交付约束

**Covers:** [F5]

**Files:**
- Modify: `skill_digest/SKILL.md:L48-L49`（第 5 步输出步骤）

- [ ] **Step 1: 在输出步骤末尾追加约束**

原 L48-L49:
```
### 5. 输出前置式简报
人会跳读，所以最重要的信息放最前面（TL;DR），细节在后。落成一个 markdown 文件交付。
```

改为：
```
### 5. 输出前置式简报
人会跳读，所以最重要的信息放最前面（TL;DR），细节在后。落成一个 markdown 文件交付。

**交付后不要在对话中附加任何评判性评论或总结。** 简报本身就是全部交付物——额外评论（如"最大亮点""最脆弱环节"）破坏了"描述不评分"的边界。若确实有非评判性的发现想补充，应在简报的"缺口"节中呈现。
```

- [ ] **Step 2: 确认改动正确**

Run: `grep "交付后不要在对话中附加" skill_digest/SKILL.md`
Expected: 输出包含该行

- [ ] **Step 3: Commit**

```bash
git add skill_digest/SKILL.md
git commit -m "fix(skill-digest): 加强交付约束，禁止附加评判性评论 (F5)"
```

---

### Task 6: 验证 — 用 skill-evaluator 重新评估

**Covers:** [F1-F8]

**Files:**
- Read: `skill_digest-eval/report.md`（旧报告，对照用）

- [ ] **Step 1: 确认所有改动已就位**

Run: `git log --oneline -5`
Expected: 5 个 fix(skill-digest) commit

- [ ] **Step 2: 用 skill-evaluator 技能重新评估 skill-digest**

重新按 skill-evaluator 流程评估修复后的 skill-digest：
- 重建 evidence.json + findings.json
- 跑 check_report.py
- 渲染新 report.md

关键验证点：
- F1: `present_files` 引用应已消失，改为对话展示
- F2: 应有自类型声明
- F3: 前置条件不再缺失
- F4: 两节有"所有类型适用"标签
- F5: 有"交付后不要附加"约束
- F8: description 有"触发词区分"

- [ ] **Step 3: 对比新老报告的 verdict**

确认新的 verdict 至少为 `pass`（预期问题已修复）。

- [ ] **Step 4: Commit 最终报告**

```bash
git add skill_digest-eval/
git commit -m "docs: skill-digest 修复后重新评估报告"
```
