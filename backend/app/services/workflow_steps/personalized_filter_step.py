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
        """
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
        
        processed_count = 0
        total_users_count = len(target_users)
        
        for uid in target_users:
             processed_count += 1
             
             # 定义局部回调适配器，用于将 filter_papers 的内部进度映射到 step 的总体进度
             # 这里的映射比较复杂，因为 filter_papers 内部是 0-100%
             # 简单起见，我们只在用户级别更新进度，或者只传递 message
             def user_filter_callback(current, total, msg):
                 # 可以在这里做更细粒度的进度计算，例如:
                 # global_progress = (processed_count - 1) / total_users_count + (current / total) / total_users_count
                 # 但为了 UI 简洁，我们主要显示 "正在处理用户 X: msg"
                 self.update_progress(processed_count, total_users_count, f"用户 {uid[:8]}...: {msg}")

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
                 
                 filter_res = paper_service.process_pending_papers(
                     uid, 
                     progress_callback=user_filter_callback,
                     manual_query=manual_query,
                     manual_authors=manual_authors,
                     manual_categories=manual_categories,
                     force=force
                 )
             else:
                 # 正常流程
                 # [Force] 获取 force 参数
                 force = context.get("force", False)
                 filter_res = paper_service.process_pending_papers(uid, progress_callback=user_filter_callback, force=force)
             
             total_input += filter_res.tokens_input or 0
             total_output += filter_res.tokens_output or 0
             total_cost += filter_res.cost or 0.0
             total_cache_hits += filter_res.cache_hit_tokens or 0
             total_requests += filter_res.request_count or 0
             
        # 记录聚合指标
        self.cost = total_cost
        self.metrics["cache_hit_tokens"] = total_cache_hits
        self.metrics["request_count"] = total_requests
        from app.core.config import settings
        self.metrics["model_name"] = settings.OPENROUTER_MODEL_CHEAP
            
        self.tokens_input = total_input
        self.tokens_output = total_output
        
        self.update_progress(100, 100, "个性化筛选完成")
        
        # Extract selected paper IDs for the next step
        selected_paper_ids = []
        if hasattr(filter_res, 'selected_papers'):
            selected_paper_ids = [p.paper_id for p in filter_res.selected_papers]
            
        return {
            "personalized_filter_completed": True,
            "selected_paper_ids": selected_paper_ids
        }
