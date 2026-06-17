#!/usr/bin/env python3
"""render_report.py — 由 evidence.json + findings.json 渲染测试报告。

三种用法：
  1) 默认模板：       python3 render_report.py evidence.json findings.json -o report.md
  2) 自定义占位符模板：python3 render_report.py evidence.json findings.json -o report.md --template my.md
  3) 导出现成片段：   python3 render_report.py evidence.json findings.json --emit-fragments frags.json
     （用于把内容手填进用户的自由文体模板——每个片段已自带 [Ex] 引用）

渲染前会先调用 check_report.validate()；机检不通过则中止（除非 --force）。
纪律强制在 evidence.json + findings.json 这两份数据上，因此无论用哪种模板，
"每条结论必有证据"都成立。换模板后若是手填，请再对成品跑 check_citations.py。
"""
import argparse
import json
import os
import re
import sys

from check_report import validate

DIMENSION_LABELS = {
    "instruction_correctness": "指令正确性",
    "consistency_completeness": "内部一致性与完整性",
    "triggering": "可触发性",
    "execution_fidelity": "执行保真度 / 遵循度",
    "outcome_quality": "产出质量",
    "efficiency": "效率",
    "safety_intent": "安全与意图一致性",
}
SEVERITY_LABELS = {"high": "高", "medium": "中", "low": "低"}
STATUS_LABELS = {"observed": "观察", "inferred": "推断"}
RESULT_LABELS = {"confirmed": "已确认", "refuted": "已推翻", "inconclusive": "无法判定"}
METHOD_LABELS = {"subagent": "subagent 独立校验", "fresh_eyes": "新视角复核", "none": "未校验"}
RATING_LABELS = {
    "pass": "通过",
    "pass_with_issues": "有问题但可用",
    "fail": "不通过",
    "inconclusive": "证据不足，无法定论",
}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _refs(ids):
    return "[" + ", ".join(ids) + "]" if ids else "[无]"


def build_fragments(evidence_doc, findings_doc):
    """把报告的每个部分渲染成带 [Ex] 引用的 markdown 片段，返回 dict。

    这个 dict 既用于填充占位符模板（{{KEY}}），也可整体导出，
    供把内容手填进用户的自由文体模板时逐段复制。"""
    findings = findings_doc.get("findings", [])
    verdict = findings_doc.get("verdict") or {}
    gaps = findings_doc.get("gaps", [])

    repl = {
        "TARGET_SKILL": evidence_doc.get("target_skill", "(未命名)"),
        "EVALUATED_AT": evidence_doc.get("evaluated_at", ""),
        "VERDICT_RATING": RATING_LABELS.get(verdict.get("rating"), verdict.get("rating", "?")),
        "VERDICT_SUMMARY": verdict.get("summary", "(未填写)"),
        "VERDICT_FINDING_REFS": _refs(verdict.get("summary_finding_ids") or []),
        "EVIDENCE_COUNT": str(len(evidence_doc.get("evidence", []))),
        "FINDINGS_COUNT": str(len(findings)),
        "HIGH_COUNT": str(sum(1 for f in findings if f.get("severity") == "high")),
        "GAPS_COUNT": str(len(gaps)),
    }

    rows = ["| ID | 类型 | 定位 | 说明 |", "| --- | --- | --- | --- |"]
    for s in evidence_doc.get("sources", []):
        rows.append(f"| {s.get('id','')} | {s.get('type','')} | {s.get('locator','')} | {s.get('note','')} |")
    repl["SOURCES_TABLE"] = "\n".join(rows)

    missing = findings_doc.get("missing_sources") or []
    repl["MISSING_SOURCES"] = "\n".join(f"- {m}" for m in missing) if missing else "_无；声明的来源均已获得。_"

    methods = {f.get("verification", {}).get("method") for f in findings
               if f.get("verification", {}).get("performed")}
    methods.discard(None)
    repl["VERIFICATION_METHOD_NOTE"] = (
        "、".join(METHOD_LABELS.get(m, m) for m in methods) if methods else "本次无高严重度发现需要校验"
    )

    blocks, by_dim = [], {}
    for f in findings:
        by_dim.setdefault(f.get("dimension", "other"), []).append(f)
    for dim, items in by_dim.items():
        blocks.append(f"### {DIMENSION_LABELS.get(dim, dim)}\n")
        for f in items:
            sev = SEVERITY_LABELS.get(f.get("severity"), f.get("severity"))
            st = STATUS_LABELS.get(f.get("status"), f.get("status"))
            blocks.append(f"**[{f.get('id')}] 严重度：{sev}　性质：{st}**")
            blocks.append(f"{f.get('statement','')}")
            blocks.append(f"- 证据：{_refs(f.get('evidence_ids') or [])}")
            if f.get("status") == "inferred" and f.get("reasoning"):
                blocks.append(f"- 推理链：{f['reasoning']}")
            ver = f.get("verification") or {}
            if ver.get("performed"):
                line = f"- 校验：{METHOD_LABELS.get(ver.get('method'), ver.get('method'))} → {RESULT_LABELS.get(ver.get('result'), ver.get('result'))}"
                if ver.get("evidence_ids"):
                    line += f"（依据 {_refs(ver['evidence_ids'])}）"
                blocks.append(line)
            blocks.append("")
    repl["FINDINGS_BY_DIMENSION"] = "\n".join(blocks) if blocks else "_本次未产生具体发现。_"

    if gaps:
        glines = []
        for g in gaps:
            gid = f"[{g['id']}] " if g.get("id") else ""
            reason = f"（原因：{g['reason']}）" if g.get("reason") else ""
            glines.append(f"- {gid}{g.get('description','')}{reason}")
        repl["GAPS_SECTION"] = "\n".join(glines)
    else:
        repl["GAPS_SECTION"] = "_无明显盲区。_"

    recs = findings_doc.get("recommendations") or []
    if recs:
        rlines = []
        for r in recs:
            if isinstance(r, dict):
                ref = f"（针对 {r['finding_id']}）" if r.get("finding_id") else ""
                rlines.append(f"- {r.get('text','')}{ref}")
            else:
                rlines.append(f"- {r}")
        repl["RECOMMENDATIONS"] = "\n".join(rlines)
    else:
        repl["RECOMMENDATIONS"] = "_无。_"

    erows = ["| ID | 来源 | 定位 | 摘录 |", "| --- | --- | --- | --- |"]
    for e in evidence_doc.get("evidence", []):
        excerpt = (e.get("excerpt", "") or "").replace("\n", " ").replace("|", "\\|")
        erows.append(f"| {e.get('id','')} | {e.get('source_id','')} | {e.get('locator','')} | {excerpt} |")
    repl["EVIDENCE_LEDGER_TABLE"] = "\n".join(erows)
    return repl


def render(template, fragments):
    out = template
    for key, val in fragments.items():
        out = out.replace("{{" + key + "}}", str(val))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evidence")
    ap.add_argument("findings")
    ap.add_argument("-o", "--output", default="report.md")
    ap.add_argument("--template", default=None, help="自定义占位符模板路径；缺省用内置默认模板")
    ap.add_argument("--emit-fragments", default=None, metavar="PATH",
                    help="把各部分现成片段导出为 JSON（用于手填自由文体模板），不渲染整篇")
    ap.add_argument("--force", action="store_true", help="即便机检失败也强行渲染")
    args = ap.parse_args()

    evidence_doc = _load(args.evidence)
    findings_doc = _load(args.findings)

    errors, _, _ = validate(evidence_doc, findings_doc)
    if errors and not args.force:
        print(f"✗ 机检未通过（{len(errors)} 处错误），已中止。先运行 check_report.py 修复，或加 --force。",
              file=sys.stderr)
        sys.exit(1)

    fragments = build_fragments(evidence_doc, findings_doc)

    # 模式 3：导出片段，供手填用户的自由文体模板
    if args.emit_fragments:
        with open(args.emit_fragments, "w", encoding="utf-8") as f:
            json.dump(fragments, f, ensure_ascii=False, indent=2)
        print(f"✓ 已导出 {len(fragments)} 个现成片段：{args.emit_fragments}")
        print("  这些片段已自带 [Ex] 引用；填入用户模板后，请对成品运行 check_citations.py 复核引用。")
        return

    # 模式 1/2：渲染占位符模板（默认或自定义）
    tpl_path = args.template or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "report-template.md")
    with open(tpl_path, encoding="utf-8") as f:
        template = f.read()

    report = render(template, fragments)

    leftover = sorted(set(re.findall(r"\{\{([A-Z_]+)\}\}", report)))
    if leftover:
        print("⚠ 模板中存在未被填充的占位符（拼写不符或本脚本不认识）：" + ", ".join(leftover), file=sys.stderr)
        print("  可用占位符见 references/report-templates.md。", file=sys.stderr)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(report)
    src = "自定义模板" if args.template else "默认模板"
    print(f"✓ 已用{src}生成报告：{args.output}")


if __name__ == "__main__":
    main()
