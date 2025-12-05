from app.core.database import get_db
import os
from dotenv import load_dotenv

load_dotenv()

class SupabasePipeline:
    """
    Supabase 数据库管道 (Stage 1)
    功能: 将爬虫抓取的 ID 和分类信息快速存入数据库。
    逻辑: 
    1. 仅存入 id, category, tags, status='pending'。
    2. 使用 upsert + ignore_duplicates=True，实现去重（若 ID 已存在则不处理）。
    """
    def __init__(self):
        self.db = get_db()

    def process_item(self, item, spider):
        # 准备插入数据 (Stage 1)
        # 注意: title, authors 等字段在此阶段为空，数据库需允许为空
        
        categories = item.get("category", [])
        
        data = {
            "id": item["id"],
            "category": categories,  # 存储所有分类 (List[str])
            "status": "pending",  # 标记为待处理
            "links": item.get("links", {}),
            # 其他 RawPaperMetadata 字段留空，等待 Stage 2 填充
            "title": None,
            "authors": None,
            "published_date": None,
            "abstract": None,
            "comment": None,
            "details": {},  # PaperAnalysis，等待 LLM 分析填充
        }
        
        try:
            # 执行 Upsert
            # on_conflict="id": 指定冲突字段
            # ignore_duplicates=True: 如果 ID 已存在，则忽略本次写入（保留旧数据，不覆盖）
            # 这样可以保证如果数据库里已经有了（无论是 pending 还是 completed），都不会被这个简单的 Stage 1 数据覆盖
            response = self.db.table("daily_papers").upsert(
                data, 
                on_conflict="id", 
                ignore_duplicates=True
            ).execute()
            
            # 统计逻辑
            if response.data:
                # 返回了数据，说明插入成功
                spider.crawler.stats.inc_value('papers/inserted')
                spider.logger.debug(f"Paper {item['id']} stored (Stage 1).")
            else:
                # 未返回数据，说明是重复项被忽略
                spider.crawler.stats.inc_value('papers/duplicates')
                spider.logger.debug(f"Paper {item['id']} ignored (Duplicate).")
            
        except Exception as e:
            spider.crawler.stats.inc_value('papers/failed')
            spider.logger.error(f"Error saving paper {item['id']}: {e}")
            
        return item


