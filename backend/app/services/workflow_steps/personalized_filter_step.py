"""
personalized_filter_step.py
工作流步骤：个性化筛选。

负责遍历所有用户，针对每个用户筛选其尚未处理的论文。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.scheduler import scheduler_service
from app.services.paper_service import paper_service

class PersonalizedFilterStep(WorkflowStep):
    """
    步骤：个性化筛选。
    """
    name = "personalized_filter"
    max_retries = 3
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行个性化筛选逻辑。
        
        遍历所有用户（或指定用户），针对每个用户筛选其尚未处理的论文。
        支持手动覆盖参数（manual_query, manual_categories, manual_authors）。
        
        Args:
            context: 工作流上下文字典，包含以下字段：
                - target_user_id (Optional[str]): 目标用户 ID，如果为空则处理所有活跃用户
                - source (Optional[str]): 来源标识，"manual" 表示手动触发
                - natural_query (Optional[str]): 手动触发时的自然语言查询
                - manual_categories (Optional[List[str]]): 手动指定的分类列表
                - manual_authors (Optional[List[str]]): 手动指定的作者列表
                - force (bool): 是否强制重新处理
                - arxiv_date (Optional[str]): ArXiv 论文发布日期
        
        Returns:
            Dict[str, Any]: 包含以下字段：
                - personalized_filter_completed (bool): 是否完成个性化筛选
                - selected_paper_ids (List[str]): 筛选出的论文 ID 列表
        """
        # ========== 获取并转换 ArXiv 日期 ==========
        # 优先从 context 获取，如果没有则从 system_status 表读取，最后 fallback 到今天
        from datetime import datetime
        from app.core.database import get_db
        import re
        
        db = get_db()
        # ========== 1. 确定论文发表日期 ==========
        # 【修复】手动查询时使用当日日期，自动任务使用 ArXiv 日期
        source = context.get("source")
        is_manual = (source == "manual")
        
        if is_manual:
            # 手动查询：使用当日日期（今天爬取的所有论文）
            iso_published_date = datetime.now().strftime("%Y-%m-%d")
            print(f"[DEBUG] 手动查询模式，使用当日日期: {iso_published_date}")
        else:
            # 自动任务：使用 ArXiv 日期
            arxiv_date = context.get("arxiv_date") # 从 context 获取
            if not arxiv_date:
                # 从 system_status 表读取最后一次 ArXiv 更新日期
                status_row = db.table("system_status").select("*").eq("key", "last_arxiv_update").execute()
                if status_row.data:
                    arxiv_date = status_row.data[0]["value"]
                    print(f"[DEBUG] 从 system_status 获取 arxiv_date: {arxiv_date}")
                else:
                    # Fallback 到今天的日期（ArXiv 格式）
                    arxiv_date = datetime.now().strftime("%A, %d %B %Y")
                    print(f"[DEBUG] 使用当前日期作为 arxiv_date: {arxiv_date}")
            
            # 【重要】转换为 ISO 格式用于数据库查询
            from app.core.utils import parse_arxiv_date
            iso_published_date = parse_arxiv_date(arxiv_date)
            print(f"[DEBUG] 日期处理: 输入='{arxiv_date}', 输出='{iso_published_date}'")
        
        
        # ========== 确定目标用户 ==========
        # 1. 确定目标用户
        target_user_id = context.get("target_user_id")
        
        target_users = []
        if target_user_id:
            target_users = [target_user_id]
            self.update_progress(0, 1, f"准备为用户 {target_user_id} 进行筛选")
        else:
            # 获取所有活跃用户
            from app.services.user_service import user_service
            target_users = user_service.get_all_active_users()
            self.update_progress(0, len(target_users), f"准备为 {len(target_users)} 位用户进行筛选")
            
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_cache_hits = 0
        total_requests = 0
        
        # [Modified] Track total accepted count
        total_accepted_count = 0
        
        # [修复] 累加所有用户的统计数据
        total_analyzed = 0
        total_rejected = 0
        
        # [新增] 初始化推荐论文ID累加列表
        # 用于收集所有用户的推荐论文ID，防止在多用户场景下数据丢失
        all_selected_paper_ids = []
        
        processed_count = 0
        total_users_count = len(target_users)
        
        for uid in target_users:
             processed_count += 1
             
             # 定义局部回调适配器，用于将 filter_papers 的内部进度映射到 step 的总体进度
             # [修复] 直接传递论文级别的进度，让前端正确显示筛选进度
             # 参数说明：
             #   current: 当前处理到第几篇论文（1-47等）
             #   total: 总论文数（如47）
             #   msg: 实时消息（如 "正在筛选: 论文标题..."）
             def user_filter_callback(current, total, msg):
                 """
                 论文筛选进度回调函数。
                 
                 Args:
                     current (int): 当前处理到第几篇论文
                     total (int): 总论文数
                     msg (str): 进度消息
                 """
                 # 直接传递论文级别的进度，而非用户级别的进度
                 # 这样前端可以正确显示 "5/47" 而不是 "1/1"
                 self.update_progress(current, total, msg)

             # [Check Manual Override]
             # 检查是否存在手动覆盖参数 (Manual Override)
             manual_query = context.get("natural_query") if context.get("source") == "manual" else None
             manual_authors = context.get("manual_authors") if context.get("source") == "manual" else None
             manual_categories = context.get("manual_categories") if context.get("source") == "manual" else None
             
             if manual_query or manual_categories:
                 print(f"[DEBUG] Using manual override for user {uid}: query={manual_query}, categories={manual_categories}")
                 # 如果存在手动查询或手动分类，调用 process_pending_papers 并传入手动参数
                 # [Force] 获取 force 参数
                 force = context.get("force", False)
                 
                 # [Modified] Pass iso_published_date to ensure we only process papers from the target date
                 filter_res = paper_service.process_pending_papers(
                     uid, 
                     progress_callback=user_filter_callback,
                     manual_query=manual_query,
                     manual_authors=manual_authors,
                     manual_categories=manual_categories,
                     force=force,
                     published_date=iso_published_date # 使用 ISO 格式
                 )
             else:
                 # 正常流程
                 # [Force] 获取 force 参数
                 force = context.get("force", False)
                 filter_res = paper_service.process_pending_papers(
                     uid, 
                     progress_callback=user_filter_callback, 
                     force=force,
                     published_date=iso_published_date # 使用 ISO 格式
                 )
             
             total_input += filter_res.tokens_input or 0
             total_output += filter_res.tokens_output or 0
             total_cost += filter_res.cost or 0.0
             total_cache_hits += filter_res.cache_hit_tokens or 0
             total_requests += filter_res.request_count or 0
             
             # [Modified] Accumulate accepted count
             total_accepted_count += filter_res.accepted_count
             # [新增] 累加总分析数和拒绝数
             total_analyzed += filter_res.total_analyzed
             total_rejected += filter_res.rejected_count
             
             # [修复] 在循环内累加当前用户的推荐论文ID
             # 说明：必须在循环内部累加，否则只会保留最后一个用户的数据
             # 使用 extend() 而非 append()，将列表元素逐个添加而非嵌套列表
             if hasattr(filter_res, 'selected_papers') and filter_res.selected_papers:
                 current_user_paper_ids = [p.paper_id for p in filter_res.selected_papers]
                 all_selected_paper_ids.extend(current_user_paper_ids)
                 print(f"[DEBUG] 用户 {uid} 推荐论文数: {len(current_user_paper_ids)}")
             
        # 记录聚合指标
        self.cost = total_cost
        self.metrics["cache_hit_tokens"] = total_cache_hits
        self.metrics["request_count"] = total_requests
        from app.core.config import settings
        # 使用通用模型配置，优先新配置，回退到旧配置以保持兼容
        self.metrics["model_name"] = getattr(settings, 'MODEL_CHEAP', settings.OPENROUTER_MODEL_CHEAP)
            
        self.tokens_input = total_input
        self.tokens_output = total_output
        
        # [验证] 检查统计数据一致性
        # 说明：total_analyzed 应该等于 accepted + rejected
        if total_analyzed != (total_accepted_count + total_rejected):
            print(f"[WARN] 统计数据不一致:")
            print(f"  - total_analyzed: {total_analyzed}")
            print(f"  - accepted + rejected: {total_accepted_count} + {total_rejected} = {total_accepted_count + total_rejected}")
            print(f"  - 差值: {total_analyzed - (total_accepted_count + total_rejected)}")
        
        # [优化] 输出详细的最终统计日志
        print(f"[INFO] ============ 个性化筛选完成 ============")
        print(f"[INFO] 总分析论文数: {total_analyzed} 篇")
        print(f"[INFO] 推荐论文数: {total_accepted_count} 篇")
        print(f"[INFO] 拒绝论文数: {total_rejected} 篇")
        print(f"[INFO] 推荐论文ID总数: {len(all_selected_paper_ids)} 个")
        print(f"[INFO] ========================================")
        
        self.update_progress(100, 100, f"已筛选 {total_analyzed} 篇论文（推荐 {total_accepted_count} 篇）")
            
        # [New] Check for manual query with no results
        is_manual = context.get("source") == "manual"
        
        if is_manual and total_accepted_count == 0:
            message = "未找到符合您查询条件的论文，请尝试调整关键词或放宽筛选条件。"
            print(f"[INFO] Manual query yielded 0 papers. Stopping workflow. Msg: {message}")
            return {
                "should_stop": True,
                "stop_reason": "no_papers_found",
                "message": message,
                "personalized_filter_completed": True,
                "selected_paper_ids": []
            }

        # [修复] 使用累加的推荐论文ID列表（包含所有用户的数据）
        return {
            "personalized_filter_completed": True,
            "selected_paper_ids": all_selected_paper_ids,  # 使用累加变量而非单个用户的数据
            # [新增] 添加实际筛选统计数据，供报告生成步骤使用
            # 这些数据反映了用户实际看到的论文数量（经过分类过滤后）
            "actually_filtered_count": total_analyzed,  # 实际筛选总数 (accepted + rejected)
            "filter_accepted_count": total_accepted_count,  # 接受的论文数
            "filter_rejected_count": total_rejected  # 拒绝的论文数
        }
