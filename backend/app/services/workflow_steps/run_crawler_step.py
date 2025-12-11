"""
run_crawler_step.py
工作流步骤：运行爬虫。

负责调用 Scrapy 爬虫抓取指定类别的论文。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.workflow_service import workflow_service

class RunCrawlerStep(WorkflowStep):
    """
    步骤：运行爬虫。
    """
    name = "run_crawler"
    max_retries = 3 # 爬虫容易受网络影响，允许重试
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行爬虫逻辑。
        
        Args:
            context: 必须包含 'categories' (List[str])
        """
        categories = context.get("categories")
        if not categories:
            # 如果没有类别，可能是不需要爬取，或者逻辑错误
            # 这里假设如果没有类别就不运行
            return {"crawler_run": False}
            
        # 调用 workflow_service 中的 run_crawler
        # 注意：workflow_service.run_crawler 内部是 subprocess 调用
        workflow_service.run_crawler(categories)
        
        return {"crawler_run": True}
