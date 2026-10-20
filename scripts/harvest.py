# -*- coding: utf-8 -*-
"""多通道采集「千万别写错」(qwbxc123) 公众号文章元数据。

通道优先级:
  1. 搜狗微信「公众号」检索 (type=1) —— 拿到账号主页与最近文章
  2. 搜狗微信「文章」检索 (type=2) —— 按关键词捞历史文章
  3. 搜狗跳转链接解析 —— 换取 mp.weixin.qq.com 真实地址
  4. profile_ext 翻页 —— 有 __biz 时可枚举历史消息

已知限制（2026-10 实测）:
  - 本机 IP 访问 weixin.sogou.com 已被要求输入验证码，且账号检索返回
    "暂无相关的官方认证订阅号"，说明该账号在搜狗索引中已不可见。
  - 无 __biz 参数时无法访问 mp.weixin.qq.com/mp/profile_ext 历史列表。
  脚本会把每次采集的通道结果写入 data/collect_log.jsonl，便于后续复盘。

用法:
    python scripts/harvest.py            # 全通道尝试
    python scripts/harvest.py --probe    # 只探活，不落库
"""
import html as htmllib
import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(DATA, "articles.json")
LOG = os.path.join(DATA, "collect_log.jsonl")

TARGET = "千万别写错"
BIZ = "qwbxc123"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

QUERIES = [
    TARGET, TARGET + " 采编", TARGET + " 规范表述", TARGET + " 错别字",
    TARGET + " 公文", TARGET + " 标点", TARGET + " 领导人", TARGET + " 机构名称",
    TARGET + " 编辑", TARGET + " 校对", TARGET + " 稿件", TARGET + " 表述",
    TARGET + " 新闻", TARGET + " 提法", TARGET + " 职务", TARGET + " 会议",
    # 第二轮扩充：按该号栏目化的选题词捞历史文章
    TARGET + " 汇总", TARGET + " 错误表述", TARGET + " 政府工作报告",
    TARGET + " 十五五", TARGET + " 两会", TARGET + " 学习教育",
    TARGET + " 常委会", TARGET + " 任免", TARGET + " 通报", TARGET + " 一图读懂",
    TARGET + " 宣传", TARGET + " 通稿", TARGET + " 规范用语", TARGET + " 发文字号",
]

# 标题尾部营销套话，入库时剥离，保留原题在 title_raw
TITLE_TAIL = re.compile(
    r"[！!，,]?\s*赶快(学习一下|关注|收藏|转发学习|转发|学起来|收藏学习)[，,]?\s*(千万别写错)?\s*$")
TITLE_TAIL2 = re.compile(r"\s*[！!]?\s*千万别写错\s*[！!]?\s*$")



def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(rec):
    rec["ts"] = now()
    os.makedirs(DATA, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def strip_tags(s):
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = htmllib.unescape(s)          # 关键：&ldquo; &rdquo; &mdash; 等实体化中文引号
    return re.sub(r"\s+", " ", s).strip()


def clean_title(t):
    """剥离标题尾部“赶快学习一下，千万别写错”套话。"""
    x = TITLE_TAIL.sub("", t)
    x = TITLE_TAIL2.sub("", x)
    return (x or t).strip(" ，,！!：:")


def key_of(title):
    """去重键：只留汉字与数字，避免标点差异导致重复入库。"""
    return re.sub(r"[^\u4e00-\u9fa5A-Za-z0-9]", "", title or "")



def make_opener():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept-Language", "zh-CN,zh;q=0.9"),
                     ("Accept", "text/html,application/xhtml+xml,*/*;q=0.8")]
    try:  # 先拿基础 cookie（SUID/SNUID），可降低验证码概率
        op.open("https://www.sogou.com/", timeout=15).read()
    except Exception as e:
        log({"channel": "bootstrap", "ok": False, "err": str(e)})
    op.addheaders = [("User-Agent", UA), ("Referer", "https://weixin.sogou.com/"),
                     ("Accept-Language", "zh-CN,zh;q=0.9")]
    return op


def fetch(op, url, timeout=25):
    try:
        h = op.open(url, timeout=timeout).read().decode("utf-8", "ignore")
    except Exception as e:
        return None, str(e)
    if "需要您协助验证" in h or "VerifyCode" in h:
        return None, "CAPTCHA"
    return h, None


def parse_accounts(html):
    out = []
    for blk in re.split(r'<li id=', html)[1:]:
        txt = strip_tags(blk)
        m = re.search(r'<a[^>]*uigs="account_name_\d+"[^>]*>(.*?)</a>', blk, re.S)
        name = strip_tags(m.group(1)) if m else ""
        wx = re.search(r'<label[^>]*>微信号：</label>\s*<span[^>]*>(.*?)</span>', blk, re.S)
        wxid = strip_tags(wx.group(1)) if wx else ""
        if name or wxid:
            out.append({"name": name, "wxid": wxid})
        if "暂无" in txt and not out:
            return []
    return out


def parse_articles(html):
    items = []
    for blk in re.split(r'<div class="txt-box">', html)[1:]:
        blk = blk.split("</li>")[0]
        m = re.search(r'<h3>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            continue
        link, title = m.group(1), strip_tags(m.group(2))
        acc = re.search(r'class="all-time-y2">(.*?)</span>', blk, re.S)
        acc = strip_tags(acc.group(1)) if acc else ""
        ts = re.search(r"timeConvert\('(\d+)'\)", blk)
        date = time.strftime("%Y-%m-%d", time.localtime(int(ts.group(1)))) if ts else ""
        summ = re.search(r'class="txt-info"[^>]*>(.*?)</p>', blk, re.S)
        summ = strip_tags(summ.group(1)) if summ else ""
        items.append({"account": acc, "title": title, "title_clean": clean_title(title),
                      "date": date, "summary": summ,
                      "sogou_link": "https://weixin.sogou.com" + link.replace("&amp;", "&"),
                      "url": "", "collected": now()})
    return items


def load_existing():
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                d = json.load(f)
            store = d if isinstance(d, dict) else {"meta": {}, "articles": d}
            # 历史数据里的 &ldquo; 类实体，读入时一并清洗
            for a in store.get("articles", []):
                a["title"] = strip_tags(a.get("title", ""))
                a["summary"] = strip_tags(a.get("summary", ""))
                a["title_clean"] = clean_title(a["title"])
            return store
        except Exception:
            pass
    return {"meta": {}, "articles": []}


def save(store):
    arts = store["articles"]
    # 同标题去重（保留最早采集到的那条，避免重复计数）
    seen, uniq = set(), []
    for a in arts:
        k = key_of(a.get("title_clean") or a.get("title"))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(a)
    store["articles"] = uniq
    uniq.sort(key=lambda x: (x.get("date") or "", x.get("title_clean") or ""), reverse=True)
    store["meta"].update({"account": TARGET, "wechat_id": BIZ, "count": len(uniq),
                          "updated": now()})
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def main():
    probe = "--probe" in sys.argv
    only_extra = "--extra" in sys.argv          # 只跑第二轮扩充词
    op = make_opener()
    store = load_existing()
    known = {key_of(a.get("title_clean") or a.get("title")) for a in store["articles"]}
    added = 0
    channel_ok = {}
    queries = QUERIES[16:] if only_extra else QUERIES
    for i, a in enumerate(sys.argv):            # --from N：验证码中断后从第 N 个检索词续跑
        if a == "--from" and i + 1 < len(sys.argv):
            queries = QUERIES[int(sys.argv[i + 1]):]


    # --- 通道1: 账号检索 ---
    accs = []
    for page in (1, 2):
        url = ("https://weixin.sogou.com/weixin?type=1&query=%s&page=%d"
               % (urllib.parse.quote(TARGET), page))
        html, err = fetch(op, url)
        log({"channel": "sogou_account", "page": page, "ok": html is not None,
             "err": err, "hits": len(parse_accounts(html)) if html else 0})
        if err:
            channel_ok["sogou_account"] = err
            break
        got = parse_accounts(html)
        accs += got
        channel_ok["sogou_account"] = "%d 个候选账号" % len(got)
        if not got:
            break
        time.sleep(3)
    for a in accs:
        print("[account]", a)

    # --- 通道2: 文章检索 ---
    for q in queries:
        for page in (1, 2, 3):
            url = ("https://weixin.sogou.com/weixin?type=2&query=%s&page=%d"
                   % (urllib.parse.quote(q), page))
            html, err = fetch(op, url)
            if err:
                log({"channel": "sogou_article", "query": q, "page": page, "ok": False, "err": err})
                channel_ok["sogou_article"] = err
                break
            items = parse_articles(html)
            hit = 0
            for it in items:
                if TARGET in (it["account"] or "") and key_of(it["title_clean"]) not in known:
                    it["query"] = q
                    store["articles"].append(it)
                    known.add(key_of(it["title_clean"]))
                    hit += 1
                    added += 1
            log({"channel": "sogou_article", "query": q, "page": page, "ok": True,
                 "items": len(items), "target_hits": hit})
            print("[%s] p%d  %d 条, 目标命中 %d" % (q, page, len(items), hit))
            if not items:
                break
            time.sleep(2.5)
        time.sleep(1.5)

    store["meta"]["channels"] = channel_ok
    if not probe:
        save(store)
    print("本次新增 %d 条，累计 %d 条" % (added, len(store["articles"])))
    if any(v in ("CAPTCHA",) for v in channel_ok.values()):
        print("!! 搜狗验证码拦截，需更换出口 IP 或人工过码后重跑")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
