#!/usr/bin/env python3
"""check_report.py — 报告机检器。

强制 skill-evaluator 的核心纪律："无事实支撑不下结论"。
用法:
    python3 check_report.py evidence.json findings.json

退出码 0 表示通过；非 0 表示存在 error，应返工后再渲染报告。
其它脚本可 import validate() 复用校验逻辑。
"""
import json
import sys

SEVERITIES = {"high", "medium", "low"}
STATUSES = {"observed", "inferred"}
SOURCE_TYPES = {"skill", "session", "external"}
VERIFY_METHODS = {"subagent", "fresh_eyes", "none"}
VERIFY_RESULTS = {"confirmed", "refuted", "inconclusive"}
VERDICT_RATINGS = {"pass", "pass_with_issues", "fail", "inconclusive"}


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(evidence_doc, findings_doc):
    """返回 (errors, warnings, stats)。errors 非空即视为机检不通过。"""
    errors, warnings = [], []

    sources = evidence_doc.get("sources", [])
    evidence = evidence_doc.get("evidence", [])
    source_ids, evidence_ids = set(), set()

    # --- sources ---
    for i, s in enumerate(sources):
        ref = f"sources[{i}]"
        sid = s.get("id")
        if not sid:
            errors.append(f"{ref}: 缺少 id")
        elif sid in source_ids:
            errors.append(f"{ref}: 重复的 source id '{sid}'")
        else:
            source_ids.add(sid)
        if s.get("type") not in SOURCE_TYPES:
            errors.append(f"{ref} ({sid}): type 必须是 {SOURCE_TYPES} 之一，当前为 {s.get('type')!r}")
        if not s.get("locator"):
            errors.append(f"{ref} ({sid}): 缺少 locator（来源没有定位等于无法核对）")

    # --- evidence ---
    for i, e in enumerate(evidence):
        ref = f"evidence[{i}]"
        eid = e.get("id")
        if not eid:
            errors.append(f"{ref}: 缺少 id")
        elif eid in evidence_ids:
            errors.append(f"{ref}: 重复的 evidence id '{eid}'")
        else:
            evidence_ids.add(eid)
        if e.get("source_id") not in source_ids:
            errors.append(f"{ref} ({eid}): source_id {e.get('source_id')!r} 未在 sources 中声明")
        if not e.get("locator"):
            errors.append(f"{ref} ({eid}): 缺少 locator（每条证据都必须能定位到原文）")
        if not e.get("excerpt"):
            warnings.append(f"{ref} ({eid}): excerpt 为空，建议补上原文摘录")

    # --- findings ---
    findings = findings_doc.get("findings", [])
    finding_ids = set()
    high_count = 0
    for i, fnd in enumerate(findings):
        ref = f"findings[{i}]"
        fid = fnd.get("id")
        if not fid:
            errors.append(f"{ref}: 缺少 id")
        elif fid in finding_ids:
            errors.append(f"{ref}: 重复的 finding id '{fid}'")
        else:
            finding_ids.add(fid)

        if not fnd.get("dimension"):
            errors.append(f"{ref} ({fid}): 缺少 dimension")
        sev = fnd.get("severity")
        if sev not in SEVERITIES:
            errors.append(f"{ref} ({fid}): severity 必须是 {SEVERITIES} 之一，当前为 {sev!r}")
        status = fnd.get("status")
        if status not in STATUSES:
            errors.append(f"{ref} ({fid}): status 必须是 {STATUSES} 之一，当前为 {status!r}")
        if not fnd.get("statement"):
            errors.append(f"{ref} ({fid}): 缺少 statement")

        # 核心纪律：每条发现必须有至少一个有效证据
        eids = fnd.get("evidence_ids") or []
        if not eids:
            errors.append(f"{ref} ({fid}): 没有任何 evidence_ids —— 无事实支撑的结论不允许作为发现")
        for ev in eids:
            if ev not in evidence_ids:
                errors.append(f"{ref} ({fid}): 引用了不存在的证据 {ev!r}")

        # 推断必须有推理链
        if status == "inferred" and not fnd.get("reasoning"):
            errors.append(f"{ref} ({fid}): status=inferred 但缺少 reasoning（推断必须摊开推理链）")

        # 高严重度必须校验
        ver = fnd.get("verification") or {}
        if sev == "high":
            high_count += 1
            if not ver.get("performed"):
                errors.append(f"{ref} ({fid}): 高严重度发现必须经过校验（verification.performed=true）")
            method = ver.get("method")
            if method not in VERIFY_METHODS or method == "none":
                errors.append(f"{ref} ({fid}): 高严重度发现的 verification.method 必须是 subagent 或 fresh_eyes")
        if ver.get("performed"):
            if ver.get("result") not in VERIFY_RESULTS:
                errors.append(f"{ref} ({fid}): verification.result 必须是 {VERIFY_RESULTS} 之一")
            if ver.get("result") == "refuted":
                errors.append(f"{ref} ({fid}): 校验结果为 refuted —— 被推翻的结论应删除或改写，不能留作发现")
            for ev in ver.get("evidence_ids") or []:
                if ev not in evidence_ids:
                    errors.append(f"{ref} ({fid}): verification 引用了不存在的证据 {ev!r}")

    # --- verdict ---
    verdict = findings_doc.get("verdict") or {}
    rating = verdict.get("rating")
    if rating not in VERDICT_RATINGS:
        errors.append(f"verdict: rating 必须是 {VERDICT_RATINGS} 之一，当前为 {rating!r}")
    for fid in verdict.get("summary_finding_ids") or []:
        if fid not in finding_ids:
            errors.append(f"verdict: summary_finding_ids 引用了不存在的发现 {fid!r}")
    if rating in {"pass_with_issues", "fail"} and not (verdict.get("summary_finding_ids")):
        warnings.append("verdict: 评级为有问题/不通过，但没有点名支撑它的发现")

    # --- gaps ---
    for i, g in enumerate(findings_doc.get("gaps", [])):
        if not g.get("description"):
            errors.append(f"gaps[{i}]: 缺少 description")

    stats = {
        "sources": len(sources),
        "evidence": len(evidence),
        "findings": len(findings),
        "high_severity": high_count,
        "gaps": len(findings_doc.get("gaps", [])),
    }
    return errors, warnings, stats


def main():
    if len(sys.argv) != 3:
        print("用法: python3 check_report.py evidence.json findings.json", file=sys.stderr)
        sys.exit(2)
    evidence_doc = _load(sys.argv[1])
    findings_doc = _load(sys.argv[2])
    errors, warnings, stats = validate(evidence_doc, findings_doc)

    print("统计:", ", ".join(f"{k}={v}" for k, v in stats.items()))
    for w in warnings:
        print(f"  ⚠ 警告: {w}")
    if errors:
        print(f"\n✗ 机检未通过，{len(errors)} 处错误：")
        for e in errors:
            print(f"  ✗ {e}")
        print("\n请补齐证据或降级结论后重试，机检通过前不要渲染报告。")
        sys.exit(1)
    print("\n✓ 机检通过：每条发现都有有效证据支撑，高严重度发现均已校验。")
    sys.exit(0)


if __name__ == "__main__":
    main()
