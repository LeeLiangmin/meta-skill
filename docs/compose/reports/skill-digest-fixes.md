---
feature: skill-digest-fixes
status: delivered
specs: []
plans:
  - docs/compose/plans/2026-06-17-skill-digest-fixes.md
branch: main
commits: 2d42cd9..cc8e6b6
---

# skill-digest 缺陷修复 — Final Report

## What Was Built

根据 skill-evaluator 评估报告的发现（F1-F8），对 skill-digest 的 `SKILL.md` 做了 5 个 commit 的集中修复，解决了 2 个高严重度和 4 个中等问题。修复后经 skill-evaluator 重新评估，verdict 从 `pass_with_issues` 提升为 `pass`。

## Architecture

单文件修改（`skill-digest/SKILL.md`），7 处改动分布在全文件的 5 个位置。

### Design Decisions

- **交付方式**: 从硬编码 `present_files` 工具名改为"默认对话展示，用户要求时落盘"——去除了对特定工具的环境依赖。
- **自类型归类**: 声明为"SOP/流程型 + 顾问/启发式型 混合"——因为五步流程是 SOP 骨架，三条边界和类型判定是顾问式原则。
- **混合型指引**: 新增"判为混合型时按主要类型走输出结构，同时在顾问型小节补充判断原则"——避免执行者因混合而遗漏信息。
- **节类型标签**: "关键观察点"和"失败模式/反目标"统一标为"所有类型适用"——与已有的"验收标准←SOP 型重点"等标签形成完整体系。
- **交付约束**: 新增"交付后不要在对话中附加任何评判性评论或总结"——直接回应本次 session 中实际发生的违规，并给出若需补充应放入"缺口"节的指引。

## Usage

skill-digest 的使用方式不变。改进后：
- 简报默认在对话中展示，不再要求特定工具
- 判断目标 skill 类型时，混合型有明确处理指引
- 交付后不再附加评判性内容

## Verification

- v2 评估：新建 `skill-digest-eval-v2/`，机检通过，verdict=pass
- 全部 6 项原发现确认已解决（V1-V6）
- 全文搜索确认 `present_files` 引用已完全移除

## Journey Log

- [lesson] 把工具名写死在 skill 里会导致跨环境不可用——交付指令应为工具无关描述或提供兜底逻辑
- [lesson] skill 自身的类型归类应显式声明，否则执行者按自己判断可能选错裁剪策略

## Source Materials

| File | Role | Notes |
|------|------|-------|
| `skill-digest-eval/report.md` | 修复前的评估报告 | verdict: pass_with_issues, 发现 F1-F8 |
| `skill-digest-eval-v2/report.md` | 修复后的重新评估 | verdict: pass, 所有发现已解决 |
| `docs/compose/plans/2026-06-17-skill-digest-fixes.md` | 实现计划 | 6 tasks, 全部完成 |
