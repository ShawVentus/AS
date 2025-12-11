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
        usage = scheduler_service.generate_report_job()
        
        if usage:
            self.tokens_input = usage.get("tokens_input", 0)
            self.tokens_output = usage.get("tokens_output", 0)
        
        return {"report_generated": True}
