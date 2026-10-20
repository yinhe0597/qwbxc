# -*- coding: utf-8 -*-
"""稿件初筛：用采编勘误词库扫描文本，输出可疑用字清单。

用法:
    python scripts/check_text.py 稿件.txt
    python scripts/check_text.py 稿件.md --md
    echo "某段文字" | python scripts/check_text.py -

输出: 控制台表格 + 可选 Markdown 报告（--md 时输出 Markdown，便于贴入审校单）

注意: 这是"初筛"工具，只报可疑点，是否修改由编辑按上下文判断。
      词库中的表述类条目（如政治提法）命中即视为必须核对。
"""
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = os.path.join(ROOT, "data", "lexicon.json")

# 命中这些类型时提示"须核对原文"
MUST_CHECK = {"政治表述", "机构名称", "职务", "规范用语", "表述", "专名"}


def load_index():
    with open(LEX, encoding="utf-8") as f:
        data = json.load(f)
    idx = []
    for e in data["entries"]:
        for w in e["wrong"]:
            w = w.strip()
            # 跳过带解释性括注的伪条目
            if not w or "（" in w or "、" in w:
                continue
            idx.append({"wrong": w, "right": e["right"], "type": e["type"],
                        "note": e.get("note", ""), "id": e["id"]})
    # 长词优先，避免短词先命中
    idx.sort(key=lambda x: -len(x["wrong"]))
    return idx


def scan(text, idx):
    hits = []
    taken = bytearray(len(text))  # 已被更长条目占用的位置
    for item in idx:
        w = item["wrong"]
        start = 0
        while True:
            p = text.find(w, start)
            if p < 0:
                break
            if not any(taken[p:p + len(w)]):
                # 防误报：年份类条目（如“98年”）不能命中“1998年”的内部
                if w[-1] in "年月日号" and w[0].isdigit():
                    if p > 0 and text[p - 1].isdigit():
                        start = p + 1
                        continue
                for k in range(p, p + len(w)):
                    taken[k] = 1
                line = text.count("\n", 0, p) + 1
                head = text.rfind("\n", 0, p) + 1
                col = p - head + 1
                ctx_a = text[max(0, p - 12):p].replace("\n", " ")
                ctx_b = text[p + len(w):p + len(w) + 12].replace("\n", " ")
                hits.append(dict(item, line=line, col=col, pos=p,
                                 ctx=ctx_a + "【" + w + "】" + ctx_b))
            start = p + 1
    hits.sort(key=lambda x: x["pos"])
    return hits


def render_console(hits, src):
    if not hits:
        return "未发现词库中的可疑用字。仍需人工通读核对事实、引文与逻辑。\n"
    out = ["%s：命中 %d 处\n" % (src, len(hits))]
    for i, h in enumerate(hits, 1):
        flag = "★" if h["type"] in MUST_CHECK else " "
        out.append("%s%2d. [%s] 第%d行 第%d列  %s → %s\n    类型：%s  %s\n    上下文：%s\n"
                   % (flag, i, h["id"], h["line"], h["col"], h["wrong"], h["right"],
                      h["type"], h["note"], h["ctx"]))
    return "".join(out)


def render_md(hits, src):
    if not hits:
        return "# 审校初筛报告\n\n源文件：`%s`\n\n未发现词库中的可疑用字。仍需人工通读核对事实、引文与逻辑。\n" % src
    L = ["# 审校初筛报告\n", "源文件：`%s` ｜ 命中 **%d** 处\n" % (src, len(hits)),
         "> ★ 表示表述类条目，须逐一核对权威原文；其余为字词线索。\n",
         "| # | 行:列 | 误 | 正 | 类型 | 说明 |", "|---|---|---|---|---|---|"]
    for i, h in enumerate(hits, 1):
        star = "★" if h["type"] in MUST_CHECK else ""
        L.append("| %d | %d:%d | %s%s | %s | %s | %s |"
                 % (i, h["line"], h["col"], star, h["wrong"], h["right"], h["type"], h["note"]))
    L.append("\n## 上下文\n")
    for i, h in enumerate(hits, 1):
        L.append("%d. `%s`\n" % (i, h["ctx"]))
    return "\n".join(L) + "\n"


def main():
    argv = sys.argv[1:]
    md = "--md" in argv
    argv = [a for a in argv if a != "--md"]
    if not argv:
        print(__doc__)
        return 2
    src = argv[0]
    if src == "-":
        text = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="ignore").read()
        name = "<stdin>"
    else:
        with open(src, encoding="utf-8", errors="ignore") as f:
            text = f.read()
        name = os.path.basename(src)
    hits = scan(text, load_index())
    sys.stdout.write(render_md(hits, name) if md else render_console(hits, name))
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
