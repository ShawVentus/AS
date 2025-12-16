"""
fetch_details_step.py
工作流步骤：获取论文详情。

负责调用 Arxiv API 获取论文的完整元数据（如摘要、作者等）。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from crawler.fetch_details import fetch_and_update_details

class FetchDetailsStep(WorkflowStep):
    """
    步骤：获取论文详情。
    """
    name = "fetch_details"
    max_retries = 3
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行获取详情逻辑。
        """
        # 调用现有的 fetch_and_update_details 函数
        # 默认针对 daily_papers 表
        # 传入 update_progress 作为回调
        fetched_count = fetch_and_update_details(table_name="daily_papers", progress_callback=self.update_progress)
        
        # [Modified] Send final progress with count
        self.update_progress(100, 100, f"共获取 {fetched_count} 篇论文")
        
        return {"details_fetched": True, "fetched_count": fetched_count}
