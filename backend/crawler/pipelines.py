from app.core.database import get_db
import json
import arxiv
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

import time

class ArxivApiPipeline:
    """
    arXiv API 数据管道
    功能: 使用爬虫抓取的 ID，调用 arXiv 官方 API 获取完整的论文元数据。
    包含: 标题、作者、摘要、发布时间、PDF链接等。
    """
    def __init__(self):
        # 初始化arxiv客户端
        # 从环境变量读取配置
        page_size = int(os.getenv("ARXIV_PAGE_SIZE", 100))
        delay_seconds = float(os.getenv("ARXIV_DELAY_SECONDS", 3.0))
        num_retries = int(os.getenv("ARXIV_NUM_RETRIES", 3))
        
        self.client = arxiv.Client(
            page_size=page_size,
            delay_seconds=delay_seconds,
            num_retries=num_retries
        )

    def process_item(self, item, spider):
        if not item.get("id"):
            return item
            
        spider.logger.info(f"Fetching details for paper {item['id']} from API...")
        
        # [FIX] 添加延迟以避免 429 错误 (针对逐个处理的情况)
        time.sleep(4) 

        try:
            # 使用ID查询论文详情
            search = arxiv.Search(id_list=[item["id"]])
            # 获取结果 (生成器)
            paper = next(self.client.results(search))
            
            self._enrich_item(item, paper)
            
            spider.logger.info(f"Successfully fetched details for {item['id']}")
            
        except StopIteration:
            spider.logger.warning(f"Paper {item['id']} not found in arXiv API")
        except Exception as e:
            spider.logger.error(f"Error fetching details for {item['id']}: {e}")
            
        return item

    def batch_process_items(self, items, spider):
        """
        批量处理论文列表，减少 API 调用次数
        手动分批处理，每批 50 个，带指数退避重试机制
        """
        if not items:
            return []

        # 提取所有 ID
        id_map = {item['id']: item for item in items if item.get('id')}
        all_ids = list(id_map.keys())
        
        if not all_ids:
            return items

        spider.logger.info(f"Batch fetching details for {len(all_ids)} papers from API...")
        
        # 手动分批，每批 50 个
        batch_size = 20
        total_processed = 0
        
        for i in range(0, len(all_ids), batch_size):
            batch_ids = all_ids[i:i + batch_size]
            spider.logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_ids)} papers...")
            
            # 重试机制
            max_retries = 5
            retry_delay = 10 # 初始等待 10 秒
            
            for attempt in range(max_retries):
                try:
                    # 批量查询
                    search = arxiv.Search(
                        id_list=batch_ids,
                        max_results=len(batch_ids)
                    )
                    results = list(self.client.results(search))
                    
                    for paper in results:
                        paper_id = paper.entry_id.split('/')[-1].split('v')[0] # 提取 ID
                        
                        # 尝试匹配 ID
                        target_item = None
                        if paper_id in id_map:
                            target_item = id_map[paper_id]
                        else:
                            # 尝试模糊匹配
                            for raw_id, item in id_map.items():
                                if raw_id in paper_id or paper_id in raw_id:
                                    target_item = item
                                    break
                        
                        if target_item:
                            self._enrich_item(target_item, paper)
                            total_processed += 1
                    
                    # 成功后跳出重试循环
                    break
                    
                except Exception as e:
                    spider.logger.error(f"Error in batch fetching (batch starting at {i}, attempt {attempt+1}): {e}")
                    
                    error_str = str(e)
                    # Retry on 429, SSL errors, and Connection errors
                    if any(x in error_str for x in ["429", "SSL", "Connection", "Max retries exceeded"]):
                        wait_time = retry_delay * (2 ** attempt) # Exponential backoff
                        spider.logger.warning(f"⚠️ Network/Rate Limit Error ({error_str}). Sleeping for {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                    else:
                        # Non-retriable error
                        spider.logger.error(f"Non-retriable error: {e}")
                        break
            
            # 批次间暂停，避免过于频繁
            if i + batch_size < len(all_ids):
                time.sleep(2)
            
        spider.logger.info(f"Successfully batch fetched details for {total_processed}/{len(all_ids)} papers")
            
        return items

    def _enrich_item(self, item, paper):
        """辅助方法：将 API 返回的 paper 对象数据填充到 item 中"""
        item["title"] = paper.title
        item["authors"] = [a.name for a in paper.authors]
        item["published_date"] = paper.published.strftime("%Y-%m-%d")
        # item["tldr"] = "" # [REMOVED] LLM生成
        item["comment"] = paper.comment if paper.comment else ""
        item["abstract"] = paper.summary # [MOVED] Top level
        
        # 更新details (移除 abstract, motivation等)
        # item["details"] = {} # [REMOVED]
        
        # 更新链接
        item["links"] = {
            "pdf": paper.pdf_url,
            "arxiv": paper.entry_id,
            "html": paper.entry_id.replace("/abs/", "/html/")
        }
        
        # 添加分类信息 (如果API返回的分类更多，可以合并)
        api_categories = paper.categories
        current_categories = item.get("category", [])
        
        # 合并并去重，保持顺序
        for cat in api_categories:
            if cat not in current_categories:
                current_categories.append(cat)
        
        item["category"] = current_categories

class SupabasePipeline:
    """
    Supabase 数据库管道
    功能: 将完整的论文数据持久化存储到 Supabase (PostgreSQL) 数据库中。
    逻辑: 检查是否存在 -> 不存在则插入。
    """
    def __init__(self):
        self.db = get_db()

    def process_item(self, item, spider):
        # 检查论文是否存在
        try:
            existing = self.db.table("papers").select("id").eq("id", item["id"]).execute()
            if existing.data:
                spider.logger.info(f"Paper {item['id']} already exists. Skipping.")
                return item
            
            # 准备插入数据
            # 注意: item["category"] 现在是一个列表
            # DB schema: category (text), tags (text[])
            
            categories = item.get("category", [])
            primary_category = categories[0] if categories else "Unknown"
            
            data = {
                "id": item["id"],
                "title": item["title"],
                "authors": item["authors"],
                "published_date": item["published_date"],
                "category": primary_category, # DB: text
                "abstract": item.get("abstract", ""), # [NEW]
                "comment": item.get("comment", ""), # [NEW]
                "links": item["links"],
                # 以下字段使用默认值或留空，等待 LLM 分析
                "tldr": None,
                "tags": categories, # 暂时将 category 存入 tags，后续 LLM 可覆盖
                "details": {},
                # "citationCount" 使用默认值 0
            }
            
            self.db.table("papers").insert(data).execute()
            spider.logger.info(f"Paper {item['id']} saved to DB.")
        except Exception as e:
            spider.logger.error(f"Error saving paper {item['id']}: {e}")
            
        return item

