# 证据账本（evidence.json）

证据账本是整套评估的地基。它把"事实"和"结论"物理分开：本文件只装可核对的事实，判断一律放到 `findings.json`。这样做的好处是，任何人（包括未来的你）都能拿着账本独立复核每一条发现，而不必相信评估者的记忆。

## schema

```json
{
  "schema_version": "1.0",
  "target_skill": "被测 skill 的名字或路径",
  "evaluated_at": "2026-06-17",
  "sources": [
    {"id": "S1", "type": "skill",    "locator": "SKILL.md",        "note": "被测 skill 主文件"},
    {"id": "S2", "type": "session",  "locator": "run-2026-06-10.jsonl", "note": "一次真实运行"},
    {"id": "S3", "type": "external", "locator": "https://docs… (fetched 2026-06-17)", "note": "官方文档"}
  ],
  "evidence": [
    {
      "id": "E1",
      "source_id": "S1",
      "locator": "L40-45",
      "excerpt": "要求在写任何代码前先 view 相关 SKILL.md",
      "status": "observed",
      "note": ""
    }
  ]
}
```

字段说明：

- `schema_version`：证据账本的格式版本号（当前 `"1.0"`）。未来若 schema 变更，此字段用于向前兼容，消费方可根据版本号选择解析策略。
- `sources[].type` 只能是 `skill` / `session` / `external` 三者之一，对应 SKILL.md 里讲的三种来源。
- `sources[].locator` 是这个来源整体的定位（文件名、运行记录名、URL+抓取日期）。
- `evidence[].source_id` 必须指向某个已声明的 source。
- `evidence[].locator` 是来源**内部**的精确位置（见下方"定位规范"）。**每条证据都必须有 locator**，没有定位的证据等于没有证据。
- `evidence[].excerpt` 是该位置的原文摘录或高精度转述。**保持简短**（几句话即可，避免整段复制），但要精确到能让人据此找到原文。
- `evidence[].status` 在账本里通常是 `observed`（直接摘录的事实）。校验得到的结论性事实也可入账，但要在 `note` 里写清来自哪次校验。

## 定位规范（locator）

精确的定位是这套方法可信的前提。三种来源各有写法：

- **skill**：`L<起>-<止>`，如 `L40-45`；引用 reference 文件时连文件名一起写，如 `references/foo.md:L12`。
- **session**：定位到回合与事件，如 `turn 7`、`turn 7 / tool_call=read_file`、`turn 9 / assistant_text`、`turn 12 / tool_result`。如果 session 没有自然的回合编号，用行号或时间戳，但要在 source 的 note 里说明编号方式。
- **external**：命令类写 `$ <命令>`并附关键输出；网页类写 URL + 抓取日期；规范类写文档名 + 章节号。

## 抽取原子事实的纪律

1. **一条证据只装一个事实。** "skill 要求先读 SKILL.md，而 session 里没读"是两个事实（一个 skill、一个 session），拆成两条 E。拆开才能让发现精确地引用。
2. **零判断。** 账本阶段不写"这是个问题""做得不好"。只写发生了什么。判断在 findings 里做，并回头引用这些 E。
3. **中立措辞。** 用"session 第 7 回合直接调用了 write_file"，而不是"session 草率地跳过了步骤"。
4. **缺失也是事实。** "session 中未出现对 SKILL.md 的读取"是一条合法且重要的 observed 证据——只要你确实通读了 session 能这么说。注意：声称"某事没发生"比声称"某事发生了"更需要你真正看全了来源，否则别这么写。

## 从 session 抽取事实的技巧

session 往往很长。建议按这个顺序扫：

- **触发与加载**：skill 是否被 consult、何时读了 SKILL.md / reference / script。
- **指令对照**：skill 里每条关键指令，在 session 里对应做了/没做/做岔了的回合。
- **工具调用序列**：调了哪些工具、顺序、有没有报错、有没有重试、有没有绕路重复劳动。
- **产出**：最终交付了什么、是否落到正确位置、是否满足 skill 声称的目标或用户的请求。
- **异常信号**：报错、自我纠正、明显的脑补/幻觉、被忽略的 bundled script（skill 提供了脚本但模型自己手写了一遍）。

把这些都先记成中立的 observed 证据，到了维度评估阶段（见 `evaluation-dimensions.md`）再据此下结论。
