from database import get_db
import json
import arxiv
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

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
        
        try:
            # 使用ID查询论文详情
            search = arxiv.Search(id_list=[item["id"]])
            # 获取结果 (生成器)
            paper = next(self.client.results(search))
            
            # 填充详细信息
            item["title"] = paper.title
            item["authors"] = [a.name for a in paper.authors]
            item["published_date"] = paper.published.strftime("%Y-%m-%d")
            item["tldr"] = "" # 仍由LLM生成
            item["comment"] = paper.comment if paper.comment else ""
            
            # 更新details
            item["details"] = {
                "abstract": paper.summary,
                "motivation": "",
                "method": "",
                "result": "",
                "conclusion": "",
                # "comment" 已移至外层，此处移除以避免重复
            }
            
            # 更新链接
            item["links"] = {
                "pdf": paper.pdf_url,
                "arxiv": paper.entry_id,
                "html": paper.entry_id.replace("/abs/", "/html/") # 修正: 替换为 /html/
            }
            
            # 添加分类信息 (如果API返回的分类更多，可以合并)
            api_categories = paper.categories
            current_categories = item.get("category", [])
            
            # 合并并去重，保持顺序
            for cat in api_categories:
                if cat not in current_categories:
                    current_categories.append(cat)
            
            item["category"] = current_categories
            # item["tags"] 已移除，使用 category 存储列表
            
            spider.logger.info(f"Successfully fetched details for {item['id']}")
            
        except StopIteration:
            spider.logger.warning(f"Paper {item['id']} not found in arXiv API")
        except Exception as e:
            spider.logger.error(f"Error fetching details for {item['id']}: {e}")
            
        return item

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
                "tldr": item["tldr"],
                "tags": categories,           # DB: text[]
                "details": item["details"],
                "links": item["links"],
                # "citationCount" 使用默认值 0
            }
            
            self.db.table("papers").insert(data).execute()
            spider.logger.info(f"Paper {item['id']} saved to DB.")
        except Exception as e:
            spider.logger.error(f"Error saving paper {item['id']}: {e}")
            
        return item

