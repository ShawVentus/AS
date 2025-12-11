"""
clear_daily_step.py
工作流步骤：清空每日数据库。

负责在开始新一轮爬取前，清空 daily_papers 表。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.paper_service import paper_service

class ClearDailyStep(WorkflowStep):
    """
    步骤：清空每日数据库。
    """
    name = "clear_daily_db"
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行清空逻辑。
        """
        success = paper_service.clear_daily_papers()
        if not success:
            raise Exception("Failed to clear daily papers database.")
            
        return {"daily_db_cleared": True}
