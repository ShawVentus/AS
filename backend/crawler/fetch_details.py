import time
import os
import arxiv
from dotenv import load_dotenv
from app.core.database import get_db

# 加载环境变量
load_dotenv()

def fetch_and_update_details():
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
    
    print("Starting Stage 2: Batch fetching paper details...")
    
    while True:
        # 1. 从 DB 获取待处理的 ID (status = 'pending')
        # 每次获取 100 个
        try:
            response = db.table("papers")\
                .select("id")\
                .eq("status", "pending")\
                .limit(100)\
                .execute()
        except Exception as e:
            print(f"Error reading database: {e}")
            time.sleep(5)
            continue
            
        papers_to_fetch = response.data
        
        if not papers_to_fetch:
            print("All pending papers updated.")
            break
            
        ids = [p['id'] for p in papers_to_fetch]
        print(f"Fetching details for {len(ids)} papers...")

        # 2. 调用 Arxiv API 批量获取
        try:
            search = arxiv.Search(id_list=ids)
            # 使用 list() 触发生成器执行
            results = list(client.results(search))
            
            updates = []
            found_ids = set()
            
            for paper in results:
                # 提取 ID (去除版本号 v1, v2...)
                paper_id = paper.entry_id.split('/')[-1].split('v')[0]
                found_ids.add(paper_id)
                
                # 构造更新数据
                # 注意: 必须包含 id 以便 upsert 识别记录
                updates.append({
                    "id": paper_id, 
                    "title": paper.title,
                    "authors": [a.name for a in paper.authors],
                    "published_date": paper.published.strftime("%Y-%m-%d"),
                    "category": paper.categories, # 更新为 API 返回的完整分类列表
                    "abstract": paper.summary,
                    "comment": paper.comment or "",
                    "links": {
                        "pdf": paper.pdf_url,
                        "arxiv": paper.entry_id,
                        "html": paper.entry_id.replace("/abs/", "/html/")
                    },
                    "status": "completed", # 标记为完成
                    # "updated_at": "now()" # Supabase 自动处理或手动添加
                })
            
            # 3. 批量更新回数据库
            if updates:
                # 使用 upsert 更新现有记录
                # 注意: Supabase-py 的 upsert 默认行为是 update if exists
                db.table("papers").upsert(updates).execute()
                print(f"Successfully updated {len(updates)} papers.")
            
            # 4. 处理 API 未找到的论文
            # 如果 API 没返回某些 ID (可能是 ID 格式错误或被 Arxiv 删除)，将其标记为 'failed'
            # 避免脚本死循环卡在这些 ID 上
            missing_ids = set(ids) - found_ids
            if missing_ids:
                print(f"Warning: {len(missing_ids)} papers not found, marking as failed. IDs: {missing_ids}")
                failed_updates = [{"id": mid, "status": "failed"} for mid in missing_ids]
                db.table("papers").upsert(failed_updates).execute()

        except Exception as e:
            print(f"API or Database Error: {e}")
            # 遇到错误休眠较长时间
            time.sleep(10) 
            
        # 批次间暂停，避免触发限流
        time.sleep(2)

if __name__ == "__main__":
    fetch_and_update_details()
