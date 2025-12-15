"""
run_crawler_step.py
工作流步骤：运行爬虫。

负责调用 Scrapy 爬虫抓取指定类别的论文。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.workflow_service import workflow_service

class RunCrawlerStep(WorkflowStep):
    """
    步骤：运行爬虫。
    """
    name = "run_crawler"
    max_retries = 3 # 爬虫容易受网络影响，允许重试
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行爬虫逻辑。
        
        Args:
            context: 必须包含 'categories' (List[str])
        """
        categories = context.get("categories")
        force = context.get("force", False)
        
        if not categories:
            self.update_progress(100, 100, "没有指定分类，跳过爬取")
            return {"crawler_run": False}
            
        # 1. 获取当前 Arxiv 日期
        # 优先从 context 获取，如果没有则假设是今天 (或者由 scheduler 注入)
        # 注意: 如果 context 中没有 date，我们可能无法准确判断 "今日已爬取"
        # 但通常 scheduler.run_daily_workflow 会先 check_arxiv_update 并放入 context
        from datetime import datetime
        import json
        from app.core.database import get_db
        
        db = get_db()
        
        # 尝试获取 Arxiv 日期，如果 context 中没有，则尝试从 system_status 获取 last_arxiv_update
        arxiv_date = context.get("arxiv_date")
        if not arxiv_date:
            status_row = db.table("system_status").select("*").eq("key", "last_arxiv_update").execute()
            if status_row.data:
                arxiv_date = status_row.data[0]["value"]
            else:
                # Fallback to today
                arxiv_date = datetime.now().strftime("%A, %d %B %Y") # Arxiv format approx
        
        # 2. 检查 system_status 中的 daily_crawl_status
        # 格式: {"date": "...", "categories": ["cs.CL"]}
        status_key = "daily_crawl_status"
        crawl_status_row = db.table("system_status").select("*").eq("key", status_key).execute()
        
        existing_categories = set()
        if crawl_status_row.data:
            try:
                status_data = crawl_status_row.data[0]
                # value 可能是字符串或 JSON 对象，取决于存储方式。Supabase client 通常返回解析后的 JSON
                val = status_data["value"]
                if isinstance(val, str):
                    val = json.loads(val)
                
                if val.get("date") == arxiv_date:
                    existing_categories = set(val.get("categories", []))
                
                print(f"[DEBUG] RunCrawlerStep: arxiv_date={arxiv_date}, status_date={val.get('date')}, existing={existing_categories}")
            except Exception as e:
                print(f"解析 daily_crawl_status 失败: {e}")
        else:
            print(f"[DEBUG] RunCrawlerStep: No daily_crawl_status found for key {status_key}")
        
        # 3. 计算需要爬取的分类
        target_categories = set(categories)
        missing_categories = list(target_categories - existing_categories)
        
        if force:
            print(f"[DEBUG] RunCrawlerStep: Force mode enabled. Target: {target_categories}, Existing: {existing_categories}, Missing: {missing_categories}")
        
        if not missing_categories:
            if force:
                print(f"[DEBUG] RunCrawlerStep: Force mode enabled. Re-crawling all target categories: {target_categories}")
                missing_categories = list(target_categories)
            else:
                self.update_progress(100, 100, f"所有分类 ({', '.join(categories)}) 已爬取，跳过")
                return {"crawler_run": False, "skipped": True}
        
        self.update_progress(0, 100, f"准备爬取: {', '.join(missing_categories)}")
        
        # 4. 运行爬虫
        try:
            workflow_service.run_crawler(missing_categories)
            
            # 5. 更新 system_status
            new_categories = list(existing_categories.union(set(missing_categories)))
            new_status = {
                "date": arxiv_date,
                "categories": new_categories,
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert
            db.table("system_status").upsert({
                "key": status_key,
                "value": new_status # Supabase 会自动处理 JSON 序列化
            }).execute()
            
            self.update_progress(100, 100, "爬取完成")
            return {"crawler_run": True, "crawled_categories": missing_categories}
            
        except Exception as e:
            self.update_progress(0, 100, f"爬虫失败: {str(e)}")
            raise e
