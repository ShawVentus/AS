"""
generate_report_step.py
工作流步骤：生成每日报告。

负责为每个用户生成日报并发送邮件。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.scheduler import scheduler_service

class GenerateReportStep(WorkflowStep):
    """
    步骤：生成每日报告。
    """
    name = "generate_report"
    max_retries = 3
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行报告生成逻辑。
        """
        force = context.get("force", False)
        target_user_id = context.get("target_user_id")
        
        # Extract manual override parameters
        manual_query = context.get("natural_query") if context.get("source") == "manual" else None
        manual_categories = context.get("manual_categories") if context.get("source") == "manual" else None
        manual_authors = context.get("manual_authors") if context.get("source") == "manual" else None
        selected_paper_ids = context.get("selected_paper_ids")
        
        stats = scheduler_service.generate_report_job(
            force=force, 
            target_user_id=target_user_id,
            progress_callback=self.update_progress,
            manual_query=manual_query,
            manual_categories=manual_categories,
            manual_authors=manual_authors,
            specific_paper_ids=selected_paper_ids
        )
        
        if stats:
            self.tokens_input = stats.get("tokens_input", 0)
            self.tokens_output = stats.get("tokens_output", 0)
            self.cost = stats.get("cost", 0.0)
            self.metrics["cache_hit_tokens"] = stats.get("cache_hit_tokens", 0)
            self.metrics["request_count"] = stats.get("request_count", 0)
            
            from app.core.config import settings
            self.metrics["model_name"] = settings.OPENROUTER_MODEL_PERFORMANCE
        
        return {"report_generated": True}
