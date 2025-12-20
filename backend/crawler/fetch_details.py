import time
from datetime import datetime
import os
import arxiv
from dotenv import load_dotenv
from app.core.database import get_db

# 加载环境变量
load_dotenv()

from typing import Optional, Callable, Dict, Any

def get_arxiv_date_from_db() -> str:
    """
    从 system_status 表读取 ArXiv 网页日期（ISO 格式）。
    
    功能：
        1. 查询 system_status 表的 latest_arxiv_date 键
        2. 返回 ISO 格式日期（如 "2025-12-19"）
        3. 如果不存在，fallback 到当前系统日期
    
    Returns:
        str: ISO 格式日期字符串 (YYYY-MM-DD)
    
    注意：
        - latest_arxiv_date 由 arxiv.py 爬虫写入
        - 已经是 ISO 格式，无需转换
    """
    db = get_db()
    try:
        # 读取 latest_arxiv_date（已经是 ISO 格式）
        result = db.table("system_status").select("value").eq("key", "latest_arxiv_date").execute()
        if result.data and result.data[0].get("value"):
            arxiv_date = result.data[0]["value"]
            print(f"[fetch_details] 使用 ArXiv 日期: {arxiv_date}")
            return arxiv_date
        else:
            # Fallback：如果数据库中没有日期，使用当前日期
            fallback_date = datetime.now().strftime("%Y-%m-%d")
            print(f"[fetch_details] 警告：未找到 ArXiv 日期，使用当前日期: {fallback_date}")
            return fallback_date
    except Exception as e:
        # 异常处理：如果数据库查询失败，使用当前日期
        fallback_date = datetime.now().strftime("%Y-%m-%d")
        print(f"[fetch_details] 错误：读取 ArXiv 日期失败 ({e})，使用当前日期: {fallback_date}")
        return fallback_date

def fetch_and_update_details(table_name: str = "papers", progress_callback: Optional[Callable[[int, int, str], None]] = None):
    """
    Stage 2: 批量获取论文详情并更新到数据库
    """
    db = get_db()
    
    # 配置 Arxiv Client
    # 增加重试次数和延迟，以应对网络波动
    client = arxiv.Client(
        page_size=100,
        delay_seconds=3.0,
        num_retries=5
    )
    
    # [新增] 获取 ArXiv 网页日期
    arxiv_date = get_arxiv_date_from_db()
    
    print(f"Starting Stage 2: Batch fetching paper details from {table_name}...")
    
    while True:
        # 1. 从 DB 获取待处理的 ID (status = 'pending')
        # 每次获取 500 个
        try:
            response = db.table(table_name)\
                .select("id")\
                .eq("status", "pending")\
                .limit(500)\
                .execute()
        except Exception as e:
            print(f"Error reading database: {e}")
            time.sleep(5)
            continue
            
        papers_to_fetch = response.data
        
        if not papers_to_fetch:
            print("All pending papers updated.")
            if progress_callback:
                progress_callback(100, 100, "所有论文详情获取完成")
            return 0 # Return 0 if no papers to fetch
            
        ids = [p['id'] for p in papers_to_fetch]
        print(f"Fetching details for {len(ids)} papers...")
        
        if progress_callback:
            progress_callback(0, len(ids), f"正在获取 {len(ids)} 篇论文详情...")

        # 2. 调用 Arxiv API 批量获取
        try:
            search = arxiv.Search(id_list=ids)
            # 使用 list() 触发生成器执行
            results = list(client.results(search))
            
            updates_map = {}
            found_ids = set()
            
            for paper in results:
                # 提取 ID (去除版本号 v1, v2...)
                paper_id = paper.entry_id.split('/')[-1].split('v')[0]
                found_ids.add(paper_id)
                
                # 构造更新数据
                # 注意: 必须包含 id 以便 upsert 识别记录
                # 使用字典去重，防止同一批次中出现重复 ID 导致 "ON CONFLICT DO UPDATE command cannot affect row a second time"
                update_item = {
                    "id": paper_id, 
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "published_date": arxiv_date,  # 使用 ArXiv 网页日期
                    "category": paper.categories or [], # 更新为 API 返回的完整分类列表，确保不为 None
                    "abstract": paper.summary,
                    "comment": paper.comment or "",
                    "links": {
                        "pdf": paper.pdf_url,
                        "arxiv": paper.entry_id,
                        "html": paper.entry_id.replace("/abs/", "/html/")
                    },
                    "status": "fetched", # 标记为已获取详情，等待分析
                    # "updated_at": "now()" # Supabase 自动处理或手动添加
                }
                updates_map[paper_id] = update_item
            
            updates = list(updates_map.values())
            
            # 3. 批量更新回数据库
            if updates:
                # 使用 upsert 更新现有记录
                # 注意: Supabase-py 的 upsert 默认行为是 update if exists
                db.table(table_name).upsert(updates).execute()
                print(f"Successfully updated {len(updates)} papers.")
            
            # 4. 处理 API 未找到的论文
            # 如果 API 没返回某些 ID (可能是 ID 格式错误或被 Arxiv 删除)，将其标记为 'failed'
            # 避免脚本死循环卡在这些 ID 上
            missing_ids = set(ids) - found_ids
            if missing_ids:
                print(f"Warning: {len(missing_ids)} papers not found, marking as failed. IDs: {missing_ids}")
                # Use update instead of upsert to avoid "null value in column category" error
                # because upsert requires all non-null columns for the INSERT case.
                # Since we know these IDs exist (we just fetched them), update is safe.
                db.table(table_name).update({"status": "failed"}).in_("id", list(missing_ids)).execute()

            # [Modified] Return count
            return len(updates)

        except Exception as e:
            print(f"API or Database Error: {e}")
            # 遇到错误休眠较长时间
            time.sleep(10) 
            return 0

if __name__ == "__main__":
    fetch_and_update_details()
