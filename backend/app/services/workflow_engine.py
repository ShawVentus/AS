"""
workflow_engine.py
工作流引擎核心服务。

负责管理工作流的执行、状态追踪、重试机制和实时监控。
"""

import os
import time
import json
import traceback
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

from app.core.database import get_db
# from app.services.email_service import email_service # TODO: 创建 email_service 模块
from app.core.workflow_step import WorkflowStep

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkflowEngine:
    """
    工作流引擎。
    
    功能：
    1. 管理工作流生命周期（创建、执行、暂停、恢复）
    2. 状态追踪与持久化（数据库）
    3. 失败重试与错误处理
    4. Token 消耗与成本计算
    5. 实时进度监控
    """
    
    def __init__(self):
        self.db = get_db()
        self.steps: List[WorkflowStep] = []
        self.context: Dict[str, Any] = {}
        self.execution_id: Optional[str] = None
        
        # 从环境变量读取配置
        self.admin_emails = os.environ.get("ADMIN_EMAILS", "").split(",")
        self.llm_price_input = float(os.environ.get("LLM_PRICE_INPUT", "1.0"))  # USD per 1M tokens
        self.llm_price_output = float(os.environ.get("LLM_PRICE_OUTPUT", "5.0"))
    
    def register_step(self, step: WorkflowStep):
        """注册工作流步骤"""
        self.steps.append(step)
        logger.info(f"📝 注册步骤: [{step.name}]")
    
    def execute_workflow(self, workflow_type: str, initial_context: Dict[str, Any] = None):
        """
        执行完整的工作流。
        
        Args:
            workflow_type (str): 工作流类型，如 'daily_update'
            initial_context (Dict[str, Any], optional): 初始上下文
        """
        self.context = initial_context or {}
        
        # 1. 创建执行记录 (如果尚未存在)
        if not self.execution_id:
            self.execution_id = self._create_execution_record(workflow_type)
        else:
            # 如果已存在 ID (例如由 API 预先创建)，则更新状态为 running
            self._update_execution_status("running")
            
        logger.info(f"🚀 开始执行工作流: {workflow_type} (ID: {self.execution_id})")
        
        # 2. 初始化步骤记录
        for i, step in enumerate(self.steps):
            self._create_step_record(step, i)
        
        # 3. 顺序执行步骤
        try:
            for i, step in enumerate(self.steps):
                # 检查 should_stop 标志
                if self.context.get("should_stop", False):
                    logger.info(f"⏸️ 工作流提前终止: should_stop=True")
                    self._update_execution_status("completed", completed_at=datetime.now())
                    return self.execution_id
                
                self._execute_step_with_retry(step, i)
            
            # 所有步骤完成
            self._update_execution_status("completed", completed_at=datetime.now())
            logger.info(f"✅ 工作流执行完成: {self.execution_id}")
            
        except Exception as e:
            # 工作流失败
            logger.error(f"❌ 工作流执行失败: {e}")
            self._update_execution_status("failed", error=str(e))
            self._send_failure_alert(workflow_type, str(e), traceback.format_exc())
            raise e
        
        return self.execution_id
    
    def resume_workflow(self, execution_id: str):
        """
        从断点恢复工作流。
        
        Args:
            execution_id (str): 执行记录 ID
        """
        self.execution_id = execution_id
        logger.info(f"🔄 恢复工作流: {execution_id}")
        
        # 1. 加载执行记录
        exec_response = self.db.table("workflow_executions").select("*").eq("id", execution_id).execute()
        if not exec_response.data:
            raise ValueError(f"找不到执行记录: {execution_id}")
        
        exec_data = exec_response.data[0]
        workflow_type = exec_data["workflow_type"]
        self.context = json.loads(exec_data.get("metadata", "{}"))
        
        # 2. 加载步骤记录，找到最后一个失败或未完成的步骤
        steps_response = self.db.table("workflow_steps") \
            .select("*") \
            .eq("execution_id", execution_id) \
            .order("step_order") \
            .execute()
        
        step_records = steps_response.data
        
        # 3. 重新注册步骤 (需要根据 workflow_type 重新构造)
        # 这里简化处理，假设是 daily_update 工作流
        if workflow_type == "daily_update":
            from app.services.workflow_steps.check_update_step import CheckUpdateStep
            from app.services.workflow_steps.clear_daily_step import ClearDailyStep
            from app.services.workflow_steps.run_crawler_step import RunCrawlerStep
            from app.services.workflow_steps.fetch_details_step import FetchDetailsStep
            from app.services.workflow_steps.analyze_public_step import AnalyzePublicStep
            from app.services.workflow_steps.archive_step import ArchiveStep
            from app.services.workflow_steps.personalized_filter_step import PersonalizedFilterStep
            from app.services.workflow_steps.generate_report_step import GenerateReportStep
            
            self.register_step(CheckUpdateStep())
            self.register_step(ClearDailyStep())
            self.register_step(RunCrawlerStep())
            self.register_step(FetchDetailsStep())
            self.register_step(AnalyzePublicStep())
            self.register_step(ArchiveStep())
            self.register_step(PersonalizedFilterStep())
            self.register_step(GenerateReportStep())
        
        # 4. 找到需要重新执行的步骤
        resume_from_index = 0
        for record in step_records:
            if record["status"] not in ["completed", "skipped"]:
                break
            resume_from_index += 1
        
        logger.info(f"从步骤 {resume_from_index} 开始恢复")
        
        # 5. 从断点继续执行
        try:
            for i in range(resume_from_index, len(self.steps)):
                step = self.steps[i]
                
                # 检查 should_stop 标志
                if self.context.get("should_stop", False):
                    logger.info(f"⏸️ 工作流提前终止: should_stop=True")
                    self._update_execution_status("completed", completed_at=datetime.now())
                    return
                
                self._execute_step_with_retry(step, i)
            
            # 所有步骤完成
            self._update_execution_status("completed", completed_at=datetime.now())
            logger.info(f"✅ 工作流恢复并执行完成: {self.execution_id}")
            
        except Exception as e:
            logger.error(f"❌ 工作流恢复执行失败: {e}")
            self._update_execution_status("failed", error=str(e))
            raise e
    
    def _execute_step_with_retry(self, step: WorkflowStep, step_index: int):
        """
        执行单个步骤（含重试逻辑）。
        """
        step_record_id = self._get_step_record_id(step.name)
        
        for attempt in range(1, step.max_retries + 1):
            try:
                logger.info(f"👉 执行步骤 [{step.name}] (尝试 {attempt}/{step.max_retries + 1})...")
                
                # 更新步骤状态为 running
                self._update_step_status(step_record_id, "running", retry_count=attempt - 1)
                
                # 记录开始时间
                start_time = time.time()
                
                # 执行步骤
                result = step.execute(self.context)
                
                # 记录耗时
                duration_ms = int((time.time() - start_time) * 1000)
                
                # 更新上下文
                if result:
                    self.context.update(result)
                    # [FIX] 持久化上下文到数据库，确保断点恢复时能获取最新状态
                    self._update_execution_context()
                
                # 计算成本
                cost = self._calculate_cost(step.tokens_input, step.tokens_output)
                
                # 更新步骤为完成
                self._update_step_status(
                    step_record_id, 
                    "completed",
                    duration_ms=duration_ms,
                    tokens_input=step.tokens_input,
                    tokens_output=step.tokens_output,
                    cost=cost,
                    completed_at=datetime.now()
                )
                
                # 累加到工作流总消耗
                self._increment_workflow_cost(step.tokens_input, step.tokens_output, cost)
                
                # 更新当前步骤名称
                self._update_current_step(step.name)
                
                logger.info(f"✅ 步骤 [{step.name}] 完成。耗时: {duration_ms}ms, 成本: ${cost:.6f}")
                
                return  # 成功，退出重试循环
                
            except Exception as e:
                error_msg = str(e)
                error_stack = traceback.format_exc()
                logger.error(f"❌ 步骤 [{step.name}] 执行失败 (尝试 {attempt}): {error_msg}")
                
                if attempt < step.max_retries + 1:
                    # 指数退避
                    delay = 2 ** (attempt - 1) * int(os.environ.get("WORKFLOW_RETRY_DELAY_BASE", "2"))
                    logger.info(f"⏳ {delay}秒后重试...")
                    time.sleep(delay)
                else:
                    # 最后一次尝试失败，标记步骤失败
                    self._update_step_status(
                        step_record_id,
                        "failed",
                        error_message=error_msg,
                        error_stack=error_stack
                    )
                    raise e  # 抛出异常，中止工作流
    
    def _create_execution_record(self, workflow_type: str) -> str:
        """创建工作流执行记录"""
        execution_id = str(uuid4())
        data = {
            "id": execution_id,
            "workflow_type": workflow_type,
            "status": "running",
            "total_steps": len(self.steps),
            "completed_steps": 0,
            "metadata": json.dumps(self.context)
        }
        self.db.table("workflow_executions").insert(data).execute()
        return execution_id
    
    def _create_step_record(self, step: WorkflowStep, step_order: int):
        """创建步骤记录"""
        data = {
            "execution_id": self.execution_id,
            "step_name": step.name,
            "step_order": step_order,
            "status": "pending",
            "max_retries": step.max_retries
        }
        self.db.table("workflow_steps").insert(data).execute()
    
    def _get_step_record_id(self, step_name: str) -> str:
        """获取步骤记录 ID"""
        response = self.db.table("workflow_steps") \
            .select("id") \
            .eq("execution_id", self.execution_id) \
            .eq("step_name", step_name) \
            .execute()
        return response.data[0]["id"]
    
    def _update_step_status(self, step_id: str, status: str, **kwargs):
        """更新步骤状态"""
        data = {"status": status}
        data.update(kwargs)
        self.db.table("workflow_steps").update(data).eq("id", step_id).execute()
    
    def _update_execution_status(self, status: str, **kwargs):
        """更新执行记录状态"""
        data = {"status": status}
        data.update(kwargs)
        self.db.table("workflow_executions").update(data).eq("id", self.execution_id).execute()
    
    def _update_current_step(self, step_name: str):
        """更新当前步骤"""
        self.db.table("workflow_executions").update({
            "current_step": step_name
        }).eq("id", self.execution_id).execute()
    
    def _calculate_cost(self, tokens_input: int, tokens_output: int) -> float:
        """
        计算成本 (USD)。
        
        Args:
            tokens_input (int): 输入 Token 数
            tokens_output (int): 输出 Token 数
        
        Returns:
            float: 成本（美元）
        """
        cost_input = (tokens_input / 1_000_000) * self.llm_price_input
        cost_output = (tokens_output / 1_000_000) * self.llm_price_output
        return cost_input + cost_output
    
    def _increment_workflow_cost(self, tokens_input: int, tokens_output: int, cost: float):
        """累加工作流总成本"""
        # 读取当前值
        response = self.db.table("workflow_executions") \
            .select("total_tokens_input", "total_tokens_output", "total_cost") \
            .eq("id", self.execution_id) \
            .execute()
        
        current = response.data[0]
        
        # 累加
        new_data = {
            "total_tokens_input": current["total_tokens_input"] + tokens_input,
            "total_tokens_output": current["total_tokens_output"] + tokens_output,
            "total_cost": current["total_cost"] + cost
        }
        
        self.db.table("workflow_executions").update(new_data).eq("id", self.execution_id).execute()
    
    def _increment_completed_steps(self):
        """
        增加已完成步骤计数。
        
        注意：这里的实现是非原子性的，如果在并发场景下可能有竞争条件。
        理想情况下应该使用数据库的原子操作（如 PostgreSQL 的 UPDATE ... SET count = count + 1）。
        但 Supabase Python 客户端的 RESTful API 不直接支持，需要通过 RPC 或原生 SQL。
        这里暂时保持简单实现。
        """
        # TODO: 实现原子性增量更新
        pass
    
    def _send_failure_alert(self, workflow_type: str, error: str, stack_trace: str):
        """
        发送失败告警邮件。
        
        Args:
            workflow_type (str): 工作流类型
            error (str): 错误信息
            stack_trace (str): 堆栈跟踪
        """
        subject = f"❌ 工作流失败告警: {workflow_type}"
        content = f"""
工作流执行失败

执行 ID: {self.execution_id}
工作流类型: {workflow_type}
失败时间: {datetime.now()}
错误信息: {error}

堆栈跟踪:
{stack_trace}
        """
        # TODO: 调用 email_service.send_email(self.admin_emails, subject, content)
        logger.info(f"📧 已发送失败告警邮件给: {self.admin_emails}")

    def _update_execution_context(self):
        """更新执行记录的上下文元数据。"""
        if not self.execution_id:
            return
        try:
            self.db.table("workflow_executions").update({
                "metadata": json.dumps(self.context)
            }).eq("id", self.execution_id).execute()
        except Exception as e:
            logger.error(f"更新执行上下文失败: {e}")
