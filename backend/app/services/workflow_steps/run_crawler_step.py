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
        执行爬虫逻辑，抓取指定类别的 ArXiv 论文。
        
        功能说明：
        1. 从 context 或 system_status 获取 ArXiv 日期
        2. 检查哪些类别已经爬取过
        3. 运行 Scrapy 爬虫抓取缺失的类别
        4. 更新 system_status 记录已爬取的类别
        5. 从数据库查询今日爬取的论文数量（使用 created_at 字段）
        
        Args:
            context (Dict[str, Any]): 工作流上下文，包含以下字段
                - categories (List[str]): 要爬取的类别列表（必需）
                - force (bool): 是否强制重新爬取（可选，默认 False）
                - arxiv_date (str): ArXiv 日期（可选）
        
        Returns:
            Dict[str, Any]: 包含以下字段
                - crawler_run (bool): 是否执行了爬虫
                - crawled_categories (List[str]): 本次爬取的类别
                - crawled_count (int): 今日爬取的论文数量
                - total_found_count (int): 同 crawled_count
                - skipped (bool): 是否跳过（可选）
        
        Raises:
            Exception: 爬虫执行失败时抛出
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
                # [修复] 跳过爬虫时，本次爬取数量应为 0
                # 原因：所有类别已爬取，本次执行没有爬取任何新论文
                # 之前的查询会得到今天所有论文数（错误！）
                print(f"[INFO] 所有分类 ({', '.join(categories)}) 已爬取，跳过爬虫")
                self.update_progress(100, 100, f"所有分类已爬取，跳过")
                
                return {
                    "crawler_run": False, 
                    "skipped": True,
                    "crawled_count": 0,  # 本次未爬取任何论文
                    "total_found_count": 0
                }
        
        
        # 4. 运行爬虫
        try:
            # [修改] 接收爬虫返回的统计数据
            crawler_stats = workflow_service.run_crawler(missing_categories)
            
            # [修复] 直接使用爬虫返回的真实数量，移除 fallback 逻辑
            # 原因说明：
            # 1. 如果爬虫解析失败，run_crawler 会抛出异常（在 workflow_service 层处理）
            # 2. 如果爬虫真的爬取0篇，yielded=0 是正常情况（类别无新论文）
            # 3. 之前的 fallback 查询数据库会得到今天所有论文数（错误的总数）
            crawled_count = crawler_stats.get("yielded", 0)
            
            print(f"[INFO] 爬虫统计: 本次提交处理 {crawled_count} 篇论文")
            
            # 5. 更新 system_status (在运行爬虫后更新，表示这些分类已爬取)
            new_categories = list(existing_categories.union(set(missing_categories)))
            new_status = {
                "date": arxiv_date,
                "categories": new_categories,
                "updated_at": datetime.now().isoformat()
            }
            
            # Upsert
            db.table("system_status").upsert({
                "key": status_key,
                "value": new_status
            }).execute()

            # 6. 返回结果（使用爬虫统计的真实数量）
            # [调试] 输出爬虫统计详情，用于验证数据流
            print(f"[DEBUG] run_crawler_step 返回值详情:")
            print(f"  - crawled_count (提交处理): {crawled_count}")
            print(f"  - unique_found (去重后): {crawler_stats.get('unique_found', 'N/A')}")
            print(f"  - total_found (原始抓取): {crawler_stats.get('total_found', 'N/A')}")
            print(f"  - skipped_category (分类不符): {crawler_stats.get('skipped_category', 'N/A')}")
            
            # [优化] 构建详细的爬虫统计消息，传递给前端显示
            unique_found = crawler_stats.get("unique_found", crawled_count)
            total_found = crawler_stats.get("total_found", crawled_count)
            skipped = crawler_stats.get("skipped_category", 0)
            
            stats_msg = (
                f"📄 发现 {unique_found} 篇论文 (原始 {total_found}) | "
                f"✅ 提交 {crawled_count} 篇 | "
                f"🚫 跳过 {skipped} 篇"
            )
            
            print(f"[INFO] 爬虫统计: {stats_msg}")
            self.update_progress(100, 100, stats_msg)
            
            return {
                "crawler_run": True, 
                "crawled_categories": missing_categories, 
                "crawled_count": crawled_count,  # 使用爬虫返回的真实数量
                "total_found_count": crawled_count
            }
            
        except Exception as e:
            # [修复] 更详细的错误处理
            error_msg = f"爬虫执行失败: {str(e)}"
            print(f"[ERROR] {error_msg}")
            self.update_progress(0, 100, error_msg)
            raise e
