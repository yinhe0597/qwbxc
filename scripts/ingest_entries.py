# -*- coding: utf-8 -*-
"""把 data/inbox.json 的候选词条按 `right` 查重后追加进 data/lexicon.json。

周更第 4 步（入库）。设计要点：
  - 机械执行「追加前按 right 查重，重复跳过」，避免人工漏查。
  - 顺带校验 id 唯一、前缀与 type 归属一致、必填字段齐全。
  - 不修改、不删除任何已有词条（删除须人工确认并在报告中写明理由）。

用法:
    python scripts/ingest_entries.py                 # 追加并清空 inbox
    python scripts/ingest_entries.py --dry-run       # 只报告，不落库
"""
import json
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = os.path.join(ROOT, "data", "lexicon.json")
INBOX = os.path.join(ROOT, "data", "inbox.json")

# id 前缀 -> 允许归属的 type（与 build_references.py 的 FILE_MAP 对应）
PREFIX_TYPES = {
    "A": ["错别字", "成语", "用字", "专名"],
    "B": ["表述", "政治表述"],
    "C": ["机构名称", "职务"],
    "D": ["标点", "数字", "计量"],
    "E": ["新闻业务"],
    "F": ["规范用语"],
    "G": ["读音"],
}


def main():
    dry = "--dry-run" in sys.argv
    with open(LEX, encoding="utf-8") as f:
        lex = json.load(f)
    with open(INBOX, encoding="utf-8") as f:
        inbox = json.load(f)

    entries = lex["entries"]
    have_right = {e.get("right", "").strip() for e in entries}
    have_id = {e["id"] for e in entries}

    added, skipped_dup, skipped_bad = [], [], []
    for c in inbox.get("items", []):
        # --- 必填与格式校验 ---
        missing = [k for k in ("id", "wrong", "right", "type") if not c.get(k)]
        if missing:
            skipped_bad.append((c.get("id", "?"), "缺字段 %s" % missing))
            continue
        if c["id"] in have_id:
            skipped_bad.append((c["id"], "id 已存在"))
            continue
        allow = PREFIX_TYPES.get(c["id"][0])
        if not allow:
            skipped_bad.append((c["id"], "id 前缀不在 A-G"))
            continue
        if c["type"] not in allow:
            skipped_bad.append((c["id"], "type=%s 不属 %s 前缀" % (c["type"], c["id"][0])))
            continue
        # --- 按 right 查重 ---
        if c["right"].strip() in have_right:
            skipped_dup.append(c["id"])
            continue
        entries.append({
            "id": c["id"],
            "wrong": c["wrong"],
            "right": c["right"],
            "type": c["type"],
            "note": c.get("note", ""),
        })
        have_right.add(c["right"].strip())
        have_id.add(c["id"])
        added.append(c)

    print("新增 %d 条；按 right 查重跳过 %d 条；格式不合格跳过 %d 条"
          % (len(added), len(skipped_dup), len(skipped_bad)))
    if skipped_dup:
        print("  重复(跳过):", "、".join(skipped_dup))
    for k, why in skipped_bad:
        print("  !! %s: %s" % (k, why))

    cnt = Counter(e["id"][0] for e in added)
    if cnt:
        print("  分类分布:", dict(sorted(cnt.items())))

    if not dry and added:
        lex["meta"]["count"] = len(entries)
        with open(LEX, "w", encoding="utf-8") as f:
            json.dump(lex, f, ensure_ascii=False, indent=2)
        inbox["items"] = []
        with open(INBOX, "w", encoding="utf-8") as f:
            json.dump(inbox, f, ensure_ascii=False, indent=2)
        print("已写入 lexicon.json，当前 %d 条；inbox 已清空" % len(entries))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
