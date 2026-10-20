# -*- coding: utf-8 -*-
"""按周窗口从 data/weekly_feed.json 生成周报，写入 reports/weekly-YYYY-MM-DD.md。

用法:
    python scripts/weekly_digest.py                 # 以今天为基准，回看 7 天
    python scripts/weekly_digest.py --days 14
    python scripts/weekly_digest.py --date 2026-10-20 --days 14
"""
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEED = os.path.join(ROOT, "data", "weekly_feed.json")
LEX = os.path.join(ROOT, "data", "lexicon.json")
REP = os.path.join(ROOT, "reports")


def parse_args():
    day, days = date.today(), 7
    for i, a in enumerate(sys.argv):
        if a == "--days" and i + 1 < len(sys.argv):
            days = int(sys.argv[i + 1])
        if a == "--date" and i + 1 < len(sys.argv):
            day = datetime.strptime(sys.argv[i + 1], "%Y-%m-%d").date()
    return day, days


def main():
    day, days = parse_args()
    start = day - timedelta(days=days - 1)
    feed = json.load(open(FEED, encoding="utf-8"))
    lex = json.load(open(LEX, encoding="utf-8"))
    meta = lex["meta"]

    items = [x for x in feed.get("items", [])
             if start.isoformat() <= (x.get("date") or "") <= day.isoformat()]
    items.sort(key=lambda x: x.get("date") or "", reverse=True)

    kinds = Counter(x.get("kind", "其他") for x in items)
    sources = Counter(x.get("source", "") for x in items)
    pts = sum(len(x.get("points") or []) for x in items)

    buf = ["# 采编情报周报 ｜ %s — %s\n\n" % (start.isoformat(), day.isoformat()),
           "> 目录定位：`sources/qwbxc123`（勘误知识源）｜ 词库版本 %s ｜ 词库 %d 条\n>\n"
           % (meta.get("version", ""), len(lex["entries"])),
           "> 口径：只收与“采编差错、规范表述、编校质量”直接相关的公开内容；"
           "政治提法、机构职务以官方原文为准。\n\n",
           "## 一、本期概览\n\n",
           "| 指标 | 数值 |\n|---|---|\n",
           "| 情报条数 | %d |\n| 可入库知识点 | %d |\n| 涉及来源 | %d |\n\n" % (len(items), pts, len(sources)),
           "| 类型 | 条数 |\n|---|---|\n"]
    for k, v in kinds.most_common():
        buf.append("| %s | %d |\n" % (k, v))
    buf.append("\n## 二、条目明细\n\n")

    for i, x in enumerate(items, 1):
        buf.append("### %d. %s（%s）\n\n" % (i, x.get("title", ""), x.get("source", "")))
        buf.append("- 日期：%s ｜ 类型：%s\n" % (x.get("date", ""), x.get("kind", "")))
        if x.get("url"):
            buf.append("- 原文：%s\n" % x["url"])
        buf.append("- 判断：%s\n" % x.get("takeaway", ""))
        if x.get("points"):
            buf.append("- 可入库要点：\n")
            for p in x["points"]:
                buf.append("  - %s\n" % p)
        buf.append("\n")

    buf.append("## 三、本周处置\n\n")
    buf.append("| 环节 | 动作 |\n|---|---|\n")
    buf.append("| 采集 | `python scripts/harvest.py`（搜狗微信多检索词，验证码会中断，用 `--from N` 续跑） |\n")
    buf.append("| 提炼 | 每条最多 5 点，格式“误 → 正 → 一句话依据” |\n")
    buf.append("| 入库 | 追加 `data/lexicon.json`，`build_references.py` 重建对照表 |\n")
    buf.append("| 复核 | 政治提法、机构职务、法规名称回到官方原文核一次 |\n\n")
    buf.append("## 四、下周关注\n\n")
    buf.append("- 目标号 10 月新发文章的正文（列表页只能拿标题与摘要，正文需在微信端查看）；\n")
    buf.append("- 各地政务新媒体三季度检查通报的**共性问题**是否出现新类型；\n")
    buf.append("- 年末临近，《咬文嚼字》年度十大语文差错通常 12 月发布，提前预留表格；\n")
    buf.append("- 机构改革后旧称残留（本轮已收 5 条，下一轮补省级机构）。\n")

    os.makedirs(REP, exist_ok=True)
    out = os.path.join(REP, "weekly-%s.md" % day.isoformat())
    open(out, "w", encoding="utf-8").write("".join(buf))
    print("写入", out, len(items), "条")

    feed["meta"]["last_issue"] = day.isoformat()
    feed["meta"]["updated"] = day.isoformat()
    json.dump(feed, open(FEED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
