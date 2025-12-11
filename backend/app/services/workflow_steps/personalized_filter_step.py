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
        # 假设我们为所有活跃用户运行筛选，或者从 context 获取特定用户
        # 这里简化为：获取所有用户并运行 (实际应分批或异步)
        # 为了演示，我们只处理 context 中指定的用户，或者如果没有指定，则处理所有活跃用户
        
        # 暂时只处理硬编码的一个用户或从 context 获取
        # 实际生产中，这应该是一个循环处理所有用户的步骤，或者分发子任务
        
        # 假设 paper_service 有一个方法 process_all_users_pending_papers
        # 但目前我们只有 process_pending_papers(user_id)
        
        # 我们先模拟处理一个用户，或者遍历所有用户
        # TODO: 实现多用户循环
        
        # 暂时不做任何操作，因为 process_pending_papers 需要 user_id
        # 假设 context 中有 user_id (如果是单用户触发)
        from app.services.user_service import user_service
        from app.core.config import settings

        user_id = context.get("user_id")
        target_users = []
        
        if user_id:
            target_users = [user_id]
        else:
            # 获取所有活跃用户
            target_users = user_service.get_all_active_users()
            
        total_input = 0
        total_output = 0
        total_cost = 0.0
        total_cache_hits = 0
        total_requests = 0
        
        for uid in target_users:
             filter_res = paper_service.process_pending_papers(uid)
             total_input += filter_res.tokens_input or 0
             total_output += filter_res.tokens_output or 0
             total_cost += filter_res.cost or 0.0
             total_cache_hits += filter_res.cache_hit_tokens or 0
             total_requests += filter_res.request_count or 0
             
        # 记录聚合指标
        self.cost = total_cost
        self.metrics["cache_hit_tokens"] = total_cache_hits
        self.metrics["request_count"] = total_requests
        self.metrics["model_name"] = settings.OPENROUTER_MODEL_CHEAP
            
        self.tokens_input = total_input
        self.tokens_output = total_output
        
        return {"personalized_filter_completed": True}
