import os
import subprocess
import sys
from typing import List, Optional, Callable, Dict, Any
from app.core.database import get_db
from app.services.paper_service import paper_service
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
from crawler.fetch_details import fetch_and_update_details

class WorkflowService:
    def __init__(self):
        self.db = get_db()

    def get_active_execution(self, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        获取当前活跃的执行记录 (running or pending)。
        """
        import json
        try:
            # 查找状态为 running 或 pending 的记录
            response = self.db.table("workflow_executions") \
                .select("*") \
                .in_("status", ["running", "pending"]) \
                .order("created_at", desc=True) \
                .execute()
            
            executions = response.data
            if not executions:
                return None
                
            for exec_record in executions:
                # 检查 metadata 中的 target_user_id
                metadata_str = exec_record.get("metadata", "{}")
                # Handle case where metadata might be dict or string
                if isinstance(metadata_str, dict):
                    metadata = metadata_str
                else:
                    metadata = json.loads(metadata_str)
                
                target_user_id = metadata.get("target_user_id")
                
                # 如果指定了 user_id，必须匹配
                if user_id:
                    if target_user_id == user_id:
                        return exec_record
                else:
                    # 如果没指定 user_id，返回第一个找到的
                    return exec_record
                    
            return None
        except Exception as e:
            print(f"Error getting active execution: {e}")
            return None

    def run_crawler(self, categories: Optional[List[str]] = None) -> Dict[str, int]:
        """
        运行 ArXiv 爬虫任务。
        
        通过 subprocess 调用 Scrapy 爬虫，抓取最新的论文数据并存入数据库。
        支持传入类别列表，如果传入则只爬取指定类别。
        
        [修改] 现在会捕获爬虫输出并解析统计数据，返回真实的爬取数量。

        Args:
            categories (Optional[List[str]]): 需要爬取的类别列表。如果不传，爬虫将使用环境变量中的默认配置。

        Returns:
            Dict[str, int]: 爬虫统计数据，包含以下字段：
                - yielded (int): 提交处理的论文数量（去重后的真实爬取数）
                - unique_found (int): 发现的唯一论文数
                - total_found (int): 总共发现的论文数（含重复）
        """
        print("Starting ArXiv Crawler...")
        try:
            # cwd should be backend root (where scrapy.cfg is)
            backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
            print(f"Running Scrapy in: {backend_root}")
            
            cmd = ["scrapy", "crawl", "arxiv"]
            
            # 如果有类别参数，通过 -a 传递给 spider
            if categories:
                categories_str = ",".join(categories)
                print(f"Crawling specific categories: {categories_str}")
                cmd.extend(["-a", f"categories={categories_str}"])
            
            # [修改] 捕获爬虫输出，以便解析统计数据
            result = subprocess.run(cmd, check=True, cwd=backend_root, 
                                   capture_output=True, text=True)
            
            # [新增] 解析爬虫输出的 JSON_STATS
            # 爬虫会在输出的最后一行打印统计数据: JSON_STATS:{...}
            import json
            
            stats = None  # 初始为 None，表示尚未成功解析
            
            # 从 stdout 中提取 JSON_STATS 行
            for line in result.stdout.split('\n'):
                if line.startswith("JSON_STATS:"):
                    json_str = line.replace("JSON_STATS:", "")
                    try:
                        stats = json.loads(json_str)
                        print(f"[DEBUG] 成功解析爬虫统计: yielded={stats.get('yielded', 0)}, unique_found={stats.get('unique_found', 0)}")
                        break  # 找到就退出循环，不再解析后续行
                    except Exception as e:
                        print(f"[ERROR] JSON_STATS 解析失败: {e}")
                        print(f"[ERROR] 原始数据: {json_str}")
            
            # [修复] 如果解析失败，抛出异常
            # 原因：解析失败说明爬虫执行有问题，不应该继续执行工作流
            if stats is None:
                print("[ERROR] 爬虫未输出有效的 JSON_STATS")
                print("[ERROR] 爬虫可能发生错误，请检查爬虫代码")
                # 只打印最后20行用于调试（避免日志过多）
                lines = result.stdout.split('\n')
                print("[DEBUG] 爬虫输出的最后20行:")
                for line in lines[-20:]:
                    print(f"  {line}")
                raise Exception("爬虫统计数据解析失败，请检查爬虫输出")
            
            print("Crawler finished.")
            return stats  # 返回统计数据
            
        except Exception as e:
            print(f"Crawler failed: {e}")
            raise e

    def analyze_public_papers(self, progress_callback: Optional[Callable[[int, int, str], None]] = None):
        """
        处理公共论文分析。
        
        获取状态为 'fetched' 的新论文，并进行公共分析（如生成 TLDR、提取 Motivation 等）。
        这些分析结果是通用的，不针对特定用户。
        
        [Modified] 分批处理：每批 20 篇，批次间等待 60 秒。

        Args:
            progress_callback (Optional[Callable]): 进度回调。

        Returns:
            None
        """
        import time
        print("Starting Public Analysis...")
        try:
            print("--- Public Analysis ---")
            # 获取尚未分析的论文 (status 为 fetched)
            response = self.db.table("daily_papers").select("*").eq("status", "fetched").execute()
            raw_papers = response.data
            
            papers_to_analyze = []
            for p in raw_papers:
                # 构造 PersonalizedPaper (analysis=None, user_state=None)
                meta_data = {
                    "id": p["id"],
                    "title": p["title"],
                    "authors": p["authors"],
                    "published_date": p["published_date"],
                    "category": p["category"],
                    "abstract": p["abstract"],
                    "links": p["links"],
                    "comment": p.get("comment")
                }
                meta = RawPaperMetadata(**meta_data)
                papers_to_analyze.append(PersonalizedPaper(meta=meta, analysis=None, user_state=None))
            
            total_papers = len(papers_to_analyze)
            
            # 统计数据
            total_stats = {
                "tokens_input": 0,
                "tokens_output": 0,
                "cost": 0.0,
                "cache_hit_tokens": 0,
                "request_count": 0
            }
            
            if total_papers > 0:
                print(f"Found {total_papers} papers needing public analysis.")
                
                # 使用配置文件中的参数
                from app.core.config import settings
                batch_size = settings.LLM_ANALYSIS_BATCH_SIZE
                delay_seconds = settings.LLM_ANALYSIS_BATCH_DELAY
                
                for i in range(0, total_papers, batch_size):
                    batch = papers_to_analyze[i:i + batch_size]
                    batch_num = i // batch_size + 1
                    total_batches = (total_papers + batch_size - 1) // batch_size
                    print(f"Processing batch {batch_num}/{total_batches} (Size: {len(batch)})...")
                    
                    # 传递 progress_callback
                    # 注意：batch_analyze_papers 内部是针对 batch 的循环
                    # 如果我们希望进度是全局的，我们需要在这里做一个适配器，或者让 batch_analyze_papers 只处理局部进度
                    # 简单起见，我们让 batch_analyze_papers 处理局部进度，但这里我们无法轻易合并
                    # 更好的方式是：在 analyze_public_papers 这里控制总进度
                    
                    # 定义局部回调适配器
                    def batch_callback(current, total, msg):
                        if progress_callback:
                            # 计算全局进度
                            # i 是当前批次的起始索引
                            global_current = i + current
                            global_total = total_papers
                            progress_callback(global_current, global_total, msg)

                    batch_stats = paper_service.batch_analyze_papers(batch, progress_callback=batch_callback)
                    
                    # 累加统计
                    if batch_stats:
                        total_stats["tokens_input"] += batch_stats.get("tokens_input", 0)
                        total_stats["tokens_output"] += batch_stats.get("tokens_output", 0)
                        total_stats["cost"] += batch_stats.get("cost", 0.0)
                        total_stats["cache_hit_tokens"] += batch_stats.get("cache_hit_tokens", 0)
                        total_stats["request_count"] += batch_stats.get("request_count", 0)
                    
                    # 如果不是最后一批，等待
                    if i + batch_size < total_papers:
                        print(f"Waiting {delay_seconds} seconds before next batch...")
                        time.sleep(delay_seconds)
            else:
                print("No papers need public analysis.")
                
            # [Modified] Add analyzed_count to stats
            total_stats["analyzed_count"] = total_papers
            
            # [Optimized] 输出所有批次的总汇总
            if total_papers > 0:
                print(f"\n{'='*60}")
                print(f"📊 总体分析汇总:")
                print(f"  - 总论文数: {total_papers} 篇")
                print(f"  - 总 Tokens: {total_stats['tokens_input']}(输入) + {total_stats['tokens_output']}(输出) = {total_stats['tokens_input'] + total_stats['tokens_output']}(总计)")
                print(f"  - 总成本: ${total_stats['cost']:.4f}")
                print(f"  - 缓存命中: {total_stats['cache_hit_tokens']} tokens")
                print(f"  - API 请求数: {total_stats['request_count']} 次")
                print(f"{'='*60}\n")
                
            return total_stats

        except Exception as e:
            print(f"Error in analyze_public_papers: {e}")
            raise e

    def process_public_papers_workflow(self, categories: Optional[List[str]] = None):
        """
        执行公共论文处理工作流。
        
        流程：
        1. 运行爬虫 (run_crawler)
        2. 获取详情 (fetch_and_update_details)
        3. 公共分析 (analyze_public_papers)
        4. 归档 (archive_daily_papers)

        Args:
            categories (Optional[List[str]]): 需要爬取的类别列表。

        Returns:
            None
        """
        print("🚀 Starting Public Papers Workflow...")
        
        try:
            # 1. Run Crawler
            print("\n🕷️  Step 1: Running Crawler...")
            self.run_crawler(categories)
            
            # 2. Fetch Details
            print("\n📥 Step 2: Fetching Details from Arxiv API...")
            fetch_and_update_details(table_name="daily_papers")
            
            # 3. Analyze
            print("\n🧠 Step 3: Running Public Analysis...")
            self.analyze_public_papers()
            
            # 4. Archive
            print("\n💾 Step 4: Archiving to Public DB...")
            if paper_service.archive_daily_papers():
                print("✅ Archiving completed.")
            else:
                print("❌ Archiving failed.")
                
            print("🎉 Public Papers Workflow Completed!")
            
        except Exception as e:
            print(f"❌ Public Papers Workflow Failed: {e}")
            # Re-raise to let caller know it failed
            raise e

workflow_service = WorkflowService()
