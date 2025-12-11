"""
workflow_step.py
工作流步骤抽象基类。

定义了所有工作流步骤必须遵循的接口。
每个具体步骤（如爬虫、分析、报告）都应继承此类并实现 `execute` 方法。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

class WorkflowStep(ABC):
    """
    工作流步骤抽象基类。
    
    Attributes:
        name (str): 步骤名称 (唯一标识符)。
        max_retries (int): 最大重试次数。
        retry_delay (int): 重试延迟 (秒)。
    """
    
    # 子类必须覆盖这些属性
    name: str = "base_step"
    max_retries: int = 3
    
    def __init__(self):
        # 运行时状态
        self.execution_id: Optional[str] = None
        self.step_id: Optional[str] = None
        self.status: str = "pending" # pending, running, completed, failed
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        
        # 性能指标
        self.tokens_input: int = 0
        self.tokens_output: int = 0
        self.cost: float = 0.0
        self.metrics: Dict[str, Any] = {}

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行步骤逻辑。
        
        Args:
            context (Dict[str, Any]): 上下文数据，包含之前步骤的输出和全局配置。
            
        Returns:
            Dict[str, Any]: 步骤执行结果，将合并到上下文中供后续步骤使用。
            
        Raises:
            Exception: 执行失败时抛出异常。
        """
        pass

    def get_cost(self) -> float:
        """
        获取当前步骤的成本 (美元)。
        
        Returns:
            float: 成本金额。
        """
        return self.cost

    def reset(self):
        """重置步骤状态 (用于重试)。"""
        self.status = "pending"
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.tokens_input = 0
        self.tokens_output = 0
        self.cost = 0.0
        self.metrics = {}
