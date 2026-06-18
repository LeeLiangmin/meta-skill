#!/usr/bin/env python3
"""check_citations.py — 对最终报告成品做引用校验。

当报告是用占位符模板渲染时，纪律已由 check_report.py 在 JSON 上保证；
但当你把内容**手填**进用户的自由文体模板时，最终成品不再经过 JSON 机检，
因此需要这一道：扫描成品里的每个 Ex 引用，确认都能在 evidence.json 里找到。
这样换什么模板都不破坏"每条结论必有证据可查"。

用法:
    python3 check_citations.py report.md evidence.json
退出码 0 通过；非 0 表示存在悬空引用。
"""
import json
import re
import sys


def main():
    if len(sys.argv) != 3:
        print("用法: python3 check_citations.py report.md evidence.json", file=sys.stderr)
        sys.exit(2)

    report_path, evidence_path = sys.argv[1], sys.argv[2]
    with open(report_path, encoding="utf-8") as f:
        lines = f.readlines()
    with open(evidence_path, encoding="utf-8") as f:
        evidence_doc = json.load(f)

    valid = {e.get("id") for e in evidence_doc.get("evidence", [])}

    # 证据引用格式为 [E1]、[E1, E2] 等。只匹配方括号内的 E 引用。
    pat = re.compile(r"\[(E\d+(?:,\s*E\d+)*)\]")
    seen = set()
    cited, dangling = set(), []
    for ln, line in enumerate(lines, 1):
        for m in pat.finditer(line):
            toks = re.findall(r"E\d+", m.group(1))
            for tok in toks:
                seen.add((ln, tok))
                cited.add(tok)
                if tok not in valid:
                    dangling.append((ln, tok, line.strip()[:80]))
    # 同时检查裸 E\d+ 引用（可能出现在非 bracket 上下文中，给 warning）
    bare_pat = re.compile(r"\bE\d+\b")
    for ln, line in enumerate(lines, 1):
        for tok in bare_pat.findall(line):
            if (ln, tok) not in seen:
                dangling.append((ln, tok, f"(裸引用，建议改用 [E] 格式) {line.strip()[:80]}"))
                cited.add(tok)

    print(f"成品引用统计：出现 {len(cited)} 个不同的 Ex，证据账本中有 {len(valid)} 条证据。")

    if not cited:
        print("⚠ 成品中没有任何 Ex 引用。若报告含结论性内容，这通常意味着结论失去了事实支撑——请检查。")
        sys.exit(1)

    unused = sorted(valid - cited, key=lambda x: int(x[1:]) if x[1:].isdigit() else 0)
    if unused:
        print("ⓘ 提示：以下证据未被成品引用（不一定是问题，可能是支撑了未写入的内容）：" + ", ".join(unused))

    if dangling:
        print(f"\n✗ 发现 {len(dangling)} 处悬空引用（指向不存在的证据）：")
        for ln, tok, ctx in dangling:
            print(f"  ✗ 第 {ln} 行 引用了 {tok}（账本中没有）：{ctx}")
        print("\n请修正引用或补齐对应证据后再交付。")
        sys.exit(1)

    print("\n✓ 引用校验通过：成品中每个 Ex 都能在证据账本中找到出处。")
    sys.exit(0)


if __name__ == "__main__":
    main()
