"""
analyze_public_step.py
工作流步骤：公共论文分析。

负责调用 LLM 对每日论文进行公共分析（如生成 TLDR、提取 Motivation 等）。
"""

from typing import Dict, Any
from app.core.workflow_step import WorkflowStep
from app.services.workflow_service import workflow_service
# 假设 workflow_service 中有获取 token 消耗的方法，或者我们需要修改 workflow_service 来返回消耗
# 目前 workflow_service.analyze_public_papers 内部调用 paper_service.batch_analyze_papers
# 我们需要修改 paper_service 以支持返回 token 消耗，或者在此步骤中估算

class AnalyzePublicStep(WorkflowStep):
    """
    步骤：公共论文分析。
    """
    name = "analyze_public_papers"
    max_retries = 3
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行公共分析逻辑。
        """
        # 调用 workflow_service 中的 analyze_public_papers
        usage = workflow_service.analyze_public_papers()
        
        # 记录消耗
        self.tokens_input = usage.get("tokens_input", 0)
        self.tokens_output = usage.get("tokens_output", 0)
        
        return {"public_analysis_completed": True}
