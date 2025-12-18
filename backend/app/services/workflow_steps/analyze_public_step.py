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
    工作流步骤：公共论文分析。
    
    功能：调用 workflow_service 进行公共分析，然后归档论文到永久表。
    """
    name = "analyze_public_papers"
    max_retries = 3
    
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行公共分析逻辑，并在分析完成后立即归档论文。
        
        Args:
            context (Dict[str, Any]): 工作流上下文，包含以下字段：
                - crawled_count (int): 本次爬取的论文数量（用于归档）
        
        Returns:
            Dict[str, Any]: 包含以下字段：
                - public_analysis_done (bool): 是否完成公共分析
                - analyzed_count (int): 分析的论文数量
        """
        # 调用 workflow_service 进行公共分析
        # 该服务内部已实现：分批处理、进度回调、Token统计等逻辑
        stats = workflow_service.analyze_public_papers(progress_callback=self.update_progress)
        
        # 记录 Token 消耗
        analyzed_count = 0
        if stats:
            self.tokens_input = stats.get("tokens_input", 0)
            self.tokens_output = stats.get("tokens_output", 0)
            self.cost = stats.get("cost", 0.0)
            self.metrics["cache_hit_tokens"] = stats.get("cache_hit_tokens", 0)
            self.metrics["request_count"] = stats.get("request_count", 0)
            analyzed_count = stats.get("analyzed_count", 0)
            
            from app.core.config import settings
            # 使用通用模型配置，优先新配置，回退到旧配置以保持兼容
            self.metrics["model_name"] = getattr(settings, 'MODEL_CHEAP', settings.OPENROUTER_MODEL_CHEAP)
        
        # 【新增】归档论文到永久表
        # 将 daily_papers 中的论文归档到 papers 表，确保数据持久化
        self._perform_archive(context, analyzed_count)
        
        return {"public_analysis_done": True, "analyzed_count": analyzed_count}
    
    def _perform_archive(self, context: Dict[str, Any], analyzed_count: int) -> None:
        """
        执行归档操作的辅助函数。
        
        功能：将 daily_papers 表中的论文归档到 papers 永久表。
        
        Args:
            context (Dict[str, Any]): 工作流上下文，包含各步骤的执行结果
            analyzed_count (int): 实际分析的论文数量（本次执行）
        
        Returns:
            None
        """
        from app.services.paper_service import paper_service
        
        # [修复] 不再基于 analyzed_count 判断是否跳过归档
        # 原因：
        # 1. archive_daily_papers() 会自动判断是否有需要归档的论文
        # 2. 即使本次分析0篇，之前可能有归档失败的论文需要重试
        # 3. 确保数据一致性，不遗漏任何归档操作
        
        # 统一的进度消息（简化前端显示）
        self.update_progress(95, 100, "正在归档论文到永久表...")
        
        # 内部日志区分不同情况
        if analyzed_count == 0:
            print("[INFO] 本次无新论文需要分析，但仍执行归档检查")
        else:
            print(f"[INFO] 准备归档 {analyzed_count} 篇已分析论文")
        
        # 执行归档（不管 analyzed_count 是多少都执行）
        success = paper_service.archive_daily_papers()
        
        if not success:
            print("[WARN] 归档失败，但继续执行工作流")
            self.update_progress(100, 100, "归档失败，请检查日志")
        else:
            # 根据 analyzed_count 显示不同的完成消息
            if analyzed_count > 0:
                self.update_progress(100, 100, f"已分析 {analyzed_count} 篇论文")
                print(f"[INFO] 归档成功，本次分析 {analyzed_count} 篇论文")
            else:
                self.update_progress(100, 100, "归档完成，本次无新分析")
                print("[INFO] 归档成功，本次无新论文需要分析")
