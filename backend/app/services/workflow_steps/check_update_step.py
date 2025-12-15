"""
check_update_step.py
工作流步骤：检查 Arxiv 更新。

负责检查 Arxiv 是否有新论文发布，并确定需要爬取的类别。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.scheduler import scheduler_service # 复用现有逻辑

class CheckUpdateStep(WorkflowStep):
    """
    步骤：检查 Arxiv 更新。
    """
    name = "check_arxiv_update"
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行检查更新逻辑。
        
        Returns:
            Dict: {
                "has_update": bool,
                "categories": List[str]
            }
        """
        # 复用 SchedulerService 中的 check_arxiv_update 逻辑
        # 注意：这里直接调用 scheduler_service 实例的方法
        categories, arxiv_date = scheduler_service.check_arxiv_update()
        
        if categories:
            return {
                "has_update": True,
                "categories": categories,
                "arxiv_date": arxiv_date
            }
        else:
            return {
                "has_update": False,
                "categories": [],
                "arxiv_date": arxiv_date,
                "should_stop": True # 通知引擎停止后续步骤
            }
