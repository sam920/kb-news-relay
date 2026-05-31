"""fetch_news.py — 在 GitHub Actions 上采集国际新闻
==================================================
运行环境：GitHub Actions (Ubuntu)
依赖：feedparser, pyyaml（已列入 requirements.txt）

工作原理：
  1. 读取 queries.yaml 中的搜索关键词
  2. 对每个关键词，通过 Google News RSS 抓取最新新闻
  3. 去重后保存为 cache/YYYY-MM-DD_{topic}.json

注意：
  - 使用 feedparser（而非手写 XML 解析），兼容 Atom/RSS 多种格式
  - Google News RSS 无需 API Key
=================================================="""  # noqa: E501

import os
import json
import hashlib
import re
from datetime import datetime

import feedparser

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_google_news_rss(query, max_items=5):
    """通过 feedparser 解析 Google News RSS，自动检测中英文"""
    results = []
    import urllib.parse

    # 自动检测是否含中文，选择对应的语言参数
    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in query)
    if has_chinese:
        locale = "hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
    else:
        locale = "hl=en&gl=US&ceid=US:en"

    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&{locale}"

    try:
        fp = feedparser.parse(url)
        if fp.bozo and fp.bozo_exception:
            err = str(fp.bozo_exception)
            # "not modified" 不算错误
            if "not modified" not in err.lower():
                print(f"    feedparser bozo: {err[:100]}")

        for entry in fp.entries[:max_items]:
            source = ""
            if hasattr(entry, "source") and entry.source:
                source = getattr(entry.source, "title", "") or ""
            if not source and hasattr(entry, "author_detail"):
                source = getattr(entry.author_detail, "name", "") or ""
            if not source:
                source = getattr(entry, "author", "") or "Google News"

            snippet = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()[:300]

            pubdate = getattr(entry, "published", "") or getattr(entry, "pubDate", "") or ""
            link = getattr(entry, "link", "") or ""

            results.append({
                "title": (getattr(entry, "title", "") or "").strip(),
                "source": source,
                "date": pubdate,
                "url": link,
                "snippet": snippet,
                "matched_query": query,
            })
    except Exception as e:
        print(f"  [WARN] feedparser failed for '{query[:30]}': {e}")

    return results


def dedup(items):
    """基于标题去重"""
    seen = set()
    result = []
    for item in items:
        title = item.get("title", "")
        if not title or len(title) < 5:
            continue
        key = hashlib.md5(title.encode("utf-8")).hexdigest()[:12]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def run():
    import yaml

    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    queries_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queries.yaml")
    with open(queries_path, "r", encoding="utf-8") as f:
        all_queries = yaml.safe_load(f)

    print(f"=== News Relay — {date_str} ===")
    print(f"Topics: {list(all_queries.keys())}\n")

    for topic, keywords in all_queries.items():
        print(f"[{topic}] 搜索 {len(keywords)} 个关键词...")
        all_items = []
        for kw in keywords:
            items = fetch_google_news_rss(kw, max_items=5)
            if items:
                print(f"  '{kw[:40]}': {len(items)} 条")
                all_items.extend(items)
            else:
                print(f"  '{kw[:40]}': 0 条")

        unique = dedup(all_items)
        print(f"  → 去重后: {len(unique)} 条")

        cache_file = os.path.join(CACHE_DIR, f"{date_str}_{topic}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "date": date_str,
                    "topic": topic,
                    "total": len(unique),
                    "items": unique[:10],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"  ✅ 已保存: {cache_file}")
        print()

    # 摘要
    summary = {"date": date_str}
    for topic in all_queries:
        cf = os.path.join(CACHE_DIR, f"{date_str}_{topic}.json")
        if os.path.exists(cf):
            with open(cf, "r", encoding="utf-8") as f:
                data = json.load(f)
            summary[topic] = {"count": data["total"]}
    summary_file = os.path.join(CACHE_DIR, f"{date_str}_summary.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Summary: {json.dumps(summary, ensure_ascii=False)}")
    print("=== Done ===")


if __name__ == "__main__":
    run()
