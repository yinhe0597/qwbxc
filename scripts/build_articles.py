# -*- coding: utf-8 -*-
"""把 data/articles.json 渲染成 references/文章清单.md（按年月分组 + 主题分类）。

用法: python scripts/build_articles.py
"""
import json
import os
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "data", "articles.json")
OUT = os.path.join(ROOT, "skills", "qwbxc-caibian-kanwu", "references", "文章清单.md")

# 主题分类：按标题关键词判定，命中即归，顺序即优先级
TOPICS = OrderedDict([
    ("机构名称", ["机构名称", "机构"]),
    ("学习教育", ["学习教育", "政绩观"]),
    ("两会与报告", ["两会", "政府工作报告", "人民代表大会", "政协"]),
    ("规划与新词", ["十五五", "规划", "新词", "热词"]),
    ("涉台表述", ["台湾", "涉台"]),
    ("会议称谓", ["常委会", "会议"]),
    ("综合勘误", ["错误表述", "不规范表述", "易错词", "错别字", "汇总"]),
])


def topic_of(title):
    for name, keys in TOPICS.items():
        if any(k in title for k in keys):
            return name
    return "其他"


def main():
    data = json.load(open(ART, encoding="utf-8"))
    arts = data.get("articles", [])
    meta = data.get("meta", {})
    arts.sort(key=lambda a: a.get("date") or "", reverse=True)

    groups = OrderedDict()
    for a in arts:
        ym = (a.get("date") or "未标日期")[:7]
        groups.setdefault(ym, []).append(a)

    buf = ["<!-- 本文件由 scripts/build_articles.py 自动生成，请修改 data/articles.json 后重新生成 -->\n\n"
           "# 文章清单\n\n",
           "> 公众号：%s（%s）｜ 定位：%s\n>\n" % (
               meta.get("account", ""), meta.get("wechat_id", ""), meta.get("positioning", "")),
           "> 已整理 %d 篇 ｜ 数据更新 %s ｜ 采集口径：%s\n>\n" % (
               len(arts), meta.get("updated", ""), meta.get("status", "")),
           "> 说明：本清单由公开检索结果（标题、日期、摘要）整理，正文原文需在微信客户端查看。\n"
           "> 只做知识提炼，不复述未经核实的细节。\n\n",
           "## 主题分布\n\n| 主题 | 篇数 |\n|---|---|\n"]
    cnt = Counter(topic_of(a.get("title_clean") or a.get("title", "")) for a in arts)
    for k, v in cnt.most_common():
        buf.append("| %s | %d |\n" % (k, v))
    buf.append("\n## 篇目\n\n")

    for ym, rows in groups.items():
        buf.append("### %s（%d 篇）\n\n" % (ym, len(rows)))
        buf.append("| 日期 | 标题 | 主题 |\n|---|---|---|\n")
        for a in rows:
            t = (a.get("title_clean") or a.get("title", "")).replace("|", "／")
            buf.append("| %s | %s | %s |\n" % (a.get("date", ""), t, topic_of(t)))
        buf.append("\n")

    open(OUT, "w", encoding="utf-8").write("".join(buf))
    print("写入", OUT, len(arts), "篇")
    print(dict(cnt))


if __name__ == "__main__":
    main()
