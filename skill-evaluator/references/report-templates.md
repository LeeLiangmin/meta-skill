# 报告模板：默认、自定义、占位符清单

本 skill 把"事实/结论"（`evidence.json` + `findings.json`）和"报告呈现"分成两层。纪律（每条结论必有证据、高严重度必校验）由 `check_report.py` 强制在**数据层**，与用什么模板无关。所以你可以自由更换报告外观，而不削弱可信度——这正是支持多种模板的底气。

报告有三条路径，按用户需求选：

## A. 默认模板

不传 `--template` 即用内置 `assets/report-template.md`。适合"没有指定格式，给我一份规范报告就行"。

```bash
python3 scripts/render_report.py <eval>/evidence.json <eval>/findings.json -o <eval>/report.md
```

## B. 自定义占位符模板（用户给的是带 {{占位符}} 的模板）

当用户的报告格式可以表达成"固定结构 + 几个填空位"时，把它写成一个 markdown 模板，在要填的地方放 `{{占位符}}`，然后：

```bash
python3 scripts/render_report.py <eval>/evidence.json <eval>/findings.json -o <eval>/report.md --template 用户模板.md
```

脚本只替换它认识的占位符；模板里多余的 `{{XXX}}` 会原样保留并在 stderr 警告（方便你发现拼写不符）。一份可直接复制改造的空白模板见 `assets/report-template-blank.md`。

**可用占位符清单**（大小写须一致）：

| 占位符 | 展开为 |
| --- | --- |
| `{{TARGET_SKILL}}` | 被测 skill 名称/路径 |
| `{{EVALUATED_AT}}` | 评估日期 |
| `{{VERDICT_RATING}}` | 总评（通过/有问题但可用/不通过/证据不足） |
| `{{VERDICT_SUMMARY}}` | 总评一段话 |
| `{{VERDICT_FINDING_REFS}}` | 支撑总评的发现编号，如 [F2, F4] |
| `{{SOURCES_TABLE}}` | 来源表（markdown 表格） |
| `{{MISSING_SOURCES}}` | 请求过但缺失的来源 |
| `{{VERIFICATION_METHOD_NOTE}}` | 校验方式（subagent / 新视角复核） |
| `{{EVIDENCE_COUNT}}` / `{{FINDINGS_COUNT}}` / `{{HIGH_COUNT}}` / `{{GAPS_COUNT}}` | 各类计数 |
| `{{FINDINGS_BY_DIMENSION}}` | 按维度组织的发现全文（含每条的证据/推理链/校验） |
| `{{GAPS_SECTION}}` | 盲区与局限 |
| `{{RECOMMENDATIONS}}` | 改进建议 |
| `{{EVIDENCE_LEDGER_TABLE}}` | 证据账本附录（markdown 表格） |

## C. 自由文体模板（用户给的是一份现成文档/格式，没有占位符）

很多团队的测试报告是固定文体（如"一、测试目的 / 二、测试环境 / 三、测试结论 / 四、缺陷列表 / 五、结论与签字"），不便改成占位符。这种情况按"导出片段 → 手填 → 复核引用"走：

1. 导出现成片段（每段已自带 `[Ex]` 引用）：

   ```bash
   python3 scripts/render_report.py <eval>/evidence.json <eval>/findings.json --emit-fragments <eval>/fragments.json
   ```

2. 打开用户的模板，把对应片段**逐段填进相应小节**。映射通常是：
   - "测试对象/环境" ← `SOURCES_TABLE`
   - "测试方法" ← `VERIFICATION_METHOD_NOTE` + 计数
   - "测试结论/缺陷列表" ← `FINDINGS_BY_DIMENSION`（缺陷即各条发现）
   - "未覆盖项/风险" ← `GAPS_SECTION`
   - "整改建议" ← `RECOMMENDATIONS`
   - "总评/结论" ← `VERDICT_*`
   - 附录 ← `EVIDENCE_LEDGER_TABLE`

3. **手填时不得丢掉 `[Ex]` 引用，也不得新增没有证据的结论。** 填完后对成品做引用校验，确保每个 Ex 仍能在账本里找到：

   ```bash
   python3 scripts/check_citations.py <eval>/最终报告.md <eval>/evidence.json
   ```

   这一步把"每条结论必有证据"重新强加到**成品**上——因为手填环节绕过了 JSON 机检，必须用它补上。

## 选哪条？

- 没指定格式 → A。
- 用户能给"结构 + 填空" → B（最省事、最不易出错）。
- 用户坚持用自己的现成文体 → C（最灵活，但要靠 check_citations.py 守住纪律）。
