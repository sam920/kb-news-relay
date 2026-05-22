"""fetch_news.py — 在 GitHub Actions 上采集国际新闻
==================================================
运行环境：GitHub Actions (Ubuntu)
依赖：feedparser, pyyaml（已列入 requirements.txt）

工作原理：
  1. 读取 queries.yaml 中的搜索关键词
  2. 对每个关键词，通过 Google News RSS 抓取最新新闻
  3. 去重后保存为 cache/YYYY-MM-DD_{topic}.json

注意：
  - Google News RSS 无需 API Key，但需能从境外服务器访问
  - GitHub Actions 的 Ubuntu 运行环境满足此条件
  - 此脚本不在本地运行，只在 GitHub Actions 上执行
=================================================="""  # noqa: E501

import os, json, hashlib, re
from datetime import datetime
from xml.etree import ElementTree

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def fetch_google_news_rss(query, max_items=5):
    """通过 Google News RSS 搜索新闻（无需 API Key）"""
    import urllib.request

    results = []
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en&gl=US&ceid=US:en"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NewsRelay/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8", errors="ignore")

        root = ElementTree.fromstring(xml_data)
        ns = {"": "http://www.w3.org/2005/Atom"}

        # Try Atom format first
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        if not entries:
            entries = root.findall(".//item")

        for entry in entries:
            if len(results) >= max_items:
                break

            title = _get_text(entry, "title")
            link = _get_text(entry, "link") or _get_attr(entry, "link", "href")
            pubdate = _get_text(entry, "published") or _get_text(entry, "pubDate")
            source = _get_source(entry)
            snippet = _get_text(entry, "description") or ""

            if not title or len(title) < 10:
                continue

            results.append({
                "title": title,
                "source": source,
                "date": pubdate,
                "url": link,
                "snippet": re.sub(r"<[^>]+>", "", snippet).strip()[:300],
                "matched_query": query,
            })
    except Exception as e:
        print(f"  [WARN] Google News RSS failed for '{query[:30]}': {e}")

    return results


def _get_text(element, tag):
    """安全获取子标签文本"""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    # Try with namespace
    child = element.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _get_attr(element, tag, attr):
    """安全获取子标签属性"""
    child = element.find(tag)
    if child is not None:
        return child.get(attr, "")
    child = element.find(f"{{http://www.w3.org/2005/Atom}}{tag}")
    if child is not None:
        return child.get(attr, "")
    return ""


def _get_source(entry):
    """提取新闻来源名称"""
    source = entry.find("source")
    if source is not None and source.text:
        return source.text.strip()
    # Try <author> or <name>
    author = entry.find("author")
    if author is not None:
        name = author.find("name") or author.find("{http://www.w3.org/2005/Atom}name")
        if name is not None and name.text:
            return name.text.strip()
    return "Google News"


def dedup(items):
    """基于标题去重（简单哈希）"""
    seen = set()
    result = []
    for item in items:
        key = hashlib.md5(item["title"].encode()).hexdigest()[:12]
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def run():
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # 读取 queries.yaml
    import yaml
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
            print(f"  '{kw[:30]}': {len(items)} 条")
            all_items.extend(items)

        # 去重
        unique = dedup(all_items)
        print(f"  → 去重后: {len(unique)} 条 (原始 {len(all_items)} 条)")

        # 保存
        cache_file = os.path.join(CACHE_DIR, f"{date_str}_{topic}.json")
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "date": date_str,
                "topic": topic,
                "total": len(unique),
                "items": unique[:10],
            }, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 已保存: {cache_file}")
        print()

    # 写入状态摘要
    summary_file = os.path.join(CACHE_DIR, f"{date_str}_summary.json")
    summary = {"date": date_str}
    for topic in all_queries:
        cf = os.path.join(CACHE_DIR, f"{date_str}_{topic}.json")
        if os.path.exists(cf):
            with open(cf, "r") as f:
                data = json.load(f)
            summary[topic] = {"count": data["total"]}
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Summary: {json.dumps(summary, ensure_ascii=False)}")
    print("=== Done ===")


if __name__ == "__main__":
    run()
