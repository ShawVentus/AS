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
    工作流步骤：归档每日论文。
    
    功能：将 daily_papers 表中的数据归档到 papers 永久表。
    """
    name = "archive_daily_papers"
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行归档逻辑。
        
        Args:
            context (Dict[str, Any]): 工作流上下文，包含以下字段：
                - crawled_count (int): 本次爬取的论文数量
        
        Returns:
            Dict[str, Any]: 包含以下字段：
                - archived (bool): 是否归档成功
        """
        # 获取本次爬取数量（而非数据库总数）
        crawled_count = context.get("crawled_count", 0)
        
        # 更新进度：显示本次爬取数量
        self.update_progress(50, 100, f"正在归档 {crawled_count} 篇新论文...")
        
        success = paper_service.archive_daily_papers()
        if not success:
            raise Exception("归档每日论文失败")
        
        # 更新最终进度
        self.update_progress(100, 100, f"已归档 {crawled_count} 篇新论文")
        
        return {"archived": True}
