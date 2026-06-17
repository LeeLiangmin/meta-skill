<!--
这是一个可直接复制改造的「占位符」测试报告模板。
- 把结构改成你团队的格式，把 {{占位符}} 放到要填内容的地方。
- 渲染：python3 scripts/render_report.py evidence.json findings.json -o report.md --template 本文件
- 全部可用占位符见 references/report-templates.md。
- 不写的占位符直接删掉即可；脚本只填它认识的，多余的占位符会原样保留并告警。
-->

# 测试报告：{{TARGET_SKILL}}

- 日期：{{EVALUATED_AT}}
- 总评：{{VERDICT_RATING}}

## 测试对象与环境
{{SOURCES_TABLE}}

## 测试方法
校验方式：{{VERIFICATION_METHOD_NOTE}}
统计：证据 {{EVIDENCE_COUNT}} 条 / 发现 {{FINDINGS_COUNT}} 条（高严重度 {{HIGH_COUNT}}）/ 盲区 {{GAPS_COUNT}} 条

## 测试结论（按维度，缺陷即各条发现）
{{FINDINGS_BY_DIMENSION}}

## 未覆盖项与风险
{{GAPS_SECTION}}

## 整改建议
{{RECOMMENDATIONS}}

## 总评
{{VERDICT_SUMMARY}}

支撑结论的发现：{{VERDICT_FINDING_REFS}}

---
## 附录：证据账本
{{EVIDENCE_LEDGER_TABLE}}
