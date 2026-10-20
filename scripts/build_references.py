# -*- coding: utf-8 -*-
"""由 data/lexicon.json 生成 Skill 的 references 对照表，并统计条目数。

用法: python scripts/build_references.py
"""
import json
import os
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = os.path.join(ROOT, "data", "lexicon.json")
REF_DIR = os.path.join(ROOT, "skills", "qwbxc-caibian-kanwu", "references")

TYPE_ORDER = ["错别字", "成语", "用字", "专名", "表述", "政治表述", "机构名称", "职务",
              "标点", "数字", "计量", "新闻业务", "规范用语"]

FILE_MAP = OrderedDict([
    ("错别字对照表.md", ["错别字", "成语", "用字", "专名"]),
    ("政治与提法表述.md", ["政治表述", "表述"]),
    ("机构名称与职务.md", ["机构名称", "职务"]),
    ("标点与数字规范.md", ["标点", "数字", "计量"]),
    ("新闻业务差错.md", ["新闻业务"]),
    ("规范用语与禁用表述.md", ["规范用语"]),
])

HEAD = """<!-- 本文件由 scripts/build_references.py 自动生成，请修改 data/lexicon.json 后重新生成 -->

# {title}

> 词库版本 {version} ｜ 更新日期 {updated} ｜ 本表 {n} 条
>
> 用法：审校时按“误 → 正 → 说明”逐条比对。专有名词、引文原貌须以权威原文为准，本表仅作线索。

| # | 误（常见写法） | 正（规范写法） | 类型 | 说明 |
|---|---|---|---|---|
"""


def main():
    with open(LEX, encoding="utf-8") as f:
        data = json.load(f)
    entries = data["entries"]
    data["meta"]["count"] = len(entries)
    with open(LEX, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.makedirs(REF_DIR, exist_ok=True)
    meta = data["meta"]
    total = 0
    for fname, types in FILE_MAP.items():
        rows = [e for e in entries if e.get("type") in types]
        if not rows:
            continue
        title = fname.replace(".md", "")
        buf = [HEAD.format(title=title, version=meta["version"],
                           updated=meta["updated"], n=len(rows))]
        for i, e in enumerate(rows, 1):
            wrong = "、".join(e["wrong"])
            note = e.get("note", "").replace("|", "／")
            buf.append("| %d | %s | %s | %s | %s |\n" % (i, wrong, e["right"], e["type"], note))
        with open(os.path.join(REF_DIR, fname), "w", encoding="utf-8") as f:
            f.write("".join(buf))
        total += len(rows)
        print("生成", fname, len(rows), "条")

    # 索引
    stat = {}
    for e in entries:
        stat[e["type"]] = stat.get(e["type"], 0) + 1
    lines = ["<!-- 自动生成 -->\n", "# 词库统计\n\n",
             "| 类型 | 条目数 |\n|---|---|\n"]
    for t in TYPE_ORDER + [k for k in stat if k not in TYPE_ORDER]:
        if t in stat:
            lines.append("| %s | %d |\n" % (t, stat[t]))
    lines.append("| **合计** | **%d** |\n" % len(entries))
    with open(os.path.join(REF_DIR, "00-词库统计.md"), "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print("合计", len(entries), "条；写入 references 共", total, "条")


if __name__ == "__main__":
    main()
