# Arxiv 爬虫两阶段运行指南

本爬虫已重构为“两阶段”模式，以提高效率并避免 API 限流。

## 准备工作 (关键!)

在运行之前，**必须**更新 Supabase 数据库结构，否则 Stage 1 无法写入数据。

请在 Supabase SQL Editor 中执行以下 SQL：

```sql
-- 1. 允许元数据为空 (适应 Stage 1)
ALTER TABLE papers ALTER COLUMN title DROP NOT NULL;
ALTER TABLE papers ALTER COLUMN authors DROP NOT NULL;
ALTER TABLE papers ALTER COLUMN published_date DROP NOT NULL;

-- 2. 添加状态字段
ALTER TABLE papers ADD COLUMN IF NOT EXISTS status text DEFAULT 'pending';
```

## Stage 1: 快速抓取 ID

此阶段仅抓取 Arxiv 列表页的 ID 和分类，不调用 API，速度极快。

```bash
# 在 backend 目录下运行
cd backend
scrapy crawl arxiv
```

运行后，数据库 `papers` 表中将出现新数据，`status` 为 `pending`，`title` 为空。

## Stage 2: 批量补全详情

此阶段从数据库读取 `pending` 状态的论文，批量调用 Arxiv API 获取详情。

```bash
# 在 backend 目录下运行
python -m crawler.fetch_details
```

(或者 `python crawler/fetch_details.py`，取决于 python path 设置)

脚本会自动循环运行，直到所有待处理论文更新完毕。

## 常见问题

- **Q: 为什么数据库里只有 ID 没有标题？**

  - A: 这是正常的 Stage 1 结果。请运行 Stage 2 脚本来补全信息。

- **Q: 遇到 429 错误怎么办？**
  - A: Stage 2 脚本内置了重试机制。如果频繁出现，请在 `fetch_details.py` 中增加 `delay_seconds`。
