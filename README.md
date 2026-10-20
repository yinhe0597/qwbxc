# qwbxc ｜ 采编勘误 Skill

面向新闻采编人员的**差错审校知识库 + 可执行检查工具 + 每周情报源**，体系对标微信公众号
「千万别写错」（ID：`qwbxc123`，江苏，采编人员培训）的勘误路数：
**先分类、再定位、后统一**。

- **235 条**可机检词库（错别字 / 成语 / 用字 / 专名 / 读音 / 政治提法 / 机构职务 / 标点数字公文 / 新闻业务 / 规范用语）
- 五道关口审校 SOP（政治关、名称关、字词关、标点数字关、业务关）
- 一键初筛脚本，输出可交差的审校单
- **16 篇**目标号文章清单 + 高校/党政/业界三类情报源清单
- 每周五更新一版（词库增量 + 周报）

## 快速上手

```bash
# 1. 稿件初筛（控制台）
python scripts/check_text.py 稿件.txt

# 2. 输出 Markdown 审校单
python scripts/check_text.py 稿件.txt --md > 审校单.md

# 3. 扩充词库后重新生成对照表
python scripts/build_references.py
```

作为 Skill 使用时，把 `skills/qwbxc-caibian-kanwu/` 放入技能目录即可，
Agent 会在"审校 / 校对 / 查错 / 勘误 / 规范表述"等请求下自动加载。

## 每周更新流程

```bash
python scripts/harvest.py            # 采集目标号列表页（验证码会中断，--from N 续跑）
python scripts/weekly_digest.py      # reports/weekly-YYYY-MM-DD.md
python scripts/build_articles.py     # references/文章清单.md
python scripts/build_references.py   # 6 张对照表 + 统计
```

## 目录结构

```
.
├── skills/qwbxc-caibian-kanwu/     # Skill 本体
│   ├── SKILL.md                    # 入口：何时用、怎么用、判据
│   ├── references/
│   │   ├── 审校SOP.md              # 五道关口逐项清单 + 审校单模板
│   │   ├── 错别字对照表.md          # 112 条（自动生成）
│   │   ├── 读音与易错字音.md        # 14 条（自动生成）
│   │   ├── 政治与提法表述.md        # 40 条（自动生成）
│   │   ├── 机构名称与职务.md        # 25 条（自动生成）
│   │   ├── 标点与数字规范.md        # 19 条（自动生成）
│   │   ├── 新闻业务差错.md          # 12 条（自动生成）
│   │   ├── 规范用语与禁用表述.md    # 13 条（自动生成）
│   │   ├── 案例与年度差错.md        # 案例复盘（含 2026-10 通报）+ 年度语文差错
│   │   ├── 情报源与周更机制.md      # 高校/党政/业界账号清单 + 巡检 SOP
│   │   ├── 文章清单.md              # 目标号 16 篇（自动生成）
│   │   └── 00-词库统计.md
├── data/
│   ├── lexicon.json                # 词库唯一数据源
│   ├── articles.json               # 公众号文章元数据
│   ├── weekly_feed.json            # 每周情报流水账
│   ├── collect_log.jsonl           # 采集通道日志
│   └── 采集说明.md                  # 账号可采集性与限制说明
├── scripts/
│   ├── harvest.py                  # 多通道采集
│   ├── check_text.py               # 稿件初筛
│   ├── build_articles.py           # 文章清单渲染
│   ├── weekly_digest.py            # 周报生成
│   └── build_references.py         # 词库 → 对照表
└── reports/                        # 每周版本说明 / 周报
```

## 口径与免责

- 词库是**线索库**，不是判决书。专有名词、引文原貌、法规条文以权威原文为准。
- 政治表述以官方通稿、权威发布为唯一依据；本仓库只做提醒，不生成新提法。
- 采集内容如与官方口径冲突，一律以官方为准。

## 更新节奏

每周五自动更新：重跑采集 → 增量入库 → 重建对照表 → 提交推送。
版本说明见 `reports/`。
