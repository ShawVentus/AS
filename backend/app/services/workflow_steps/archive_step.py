"""
archive_step.py
工作流步骤：归档每日论文。

负责将 daily_papers 表中的数据归档到 papers 表。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.paper_service import paper_service

class ArchiveStep(WorkflowStep):
    """
    步骤：归档每日论文。
    """
    name = "archive_daily_papers"
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行归档逻辑。
        """
        success = paper_service.archive_daily_papers()
        if not success:
            raise Exception("Failed to archive daily papers.")
            
        return {"archived": True}
