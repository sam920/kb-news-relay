# KB News Relay — 国际新闻中继

通过 GitHub Actions 定时采集国际新闻（Google News RSS），
解决国内环境无法直接访问国际新闻源的问题。

## 使用流程

### 1. 创建 GitHub 仓库

在 GitHub 上创建一个**公开仓库**（public repo），
例如 `yourname/kb-news-relay`。

### 2. 推送代码

```bash
cd d:\BaiduSyncdisk\文档\_kb_system\news_relay
git init
git add .
git commit -m "init: news relay"
git remote add origin https://github.com/yourname/kb-news-relay.git
git branch -M main
git push -u origin main
```

### 3. 启用 GitHub Actions

推送后，GitHub Actions 会自动按以下时间运行：
- UTC 02:00 / 08:00 / 14:00 / 20:00
- (北京时间 10:00 / 16:00 / 22:00 / 04:00)

可手动在 Actions 页面点击 "Run workflow" 立即测试。

### 4. 本地使用

`collect_news.py` 会自动从以下 URL 拉取新闻数据：
```
https://raw.githubusercontent.com/yourname/kb-news-relay/main/cache/
```

默认仓库名 `kb-news-relay`，可在 `collect_news.py` 中配置。

## 文件结构

```
news_relay/
├── .github/workflows/fetch-news.yml   # GitHub Actions 工作流
├── fetch_news.py                       # 新闻采集脚本（仅 GitHub Actions 运行）
├── queries.yaml                        # 搜索关键词配置（可随时修改）
├── requirements.txt                    # Python 依赖
├── .gitignore                          # Git 忽略规则
└── cache/                              # 新闻缓存输出目录
    ├── YYYY-MM-DD_鹦鹉养殖.json
    ├── YYYY-MM-DD_肽类产品.json
    └── YYYY-MM-DD_summary.json
```

## 维护

- **加新关键词**：修改 `queries.yaml` 后 push 即可
- **改采集频次**：修改 `.github/workflows/fetch-news.yml` 中的 cron 表达式
