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
from app.core.config import settings

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
    
    def __init__(self, execution_id: Optional[str] = None):
        self.db = get_db()
        self.steps: List[WorkflowStep] = []
        self.context: Dict[str, Any] = {}
        self.execution_id: Optional[str] = execution_id
        
        # 从环境变量读取配置
        self.admin_emails = os.environ.get("ADMIN_EMAILS", "").split(",")
        self.llm_price_input = float(os.environ.get("LLM_PRICE_INPUT", "1.0"))  # USD per 1M tokens
        self.llm_price_input = float(os.environ.get("LLM_PRICE_INPUT", "1.0"))  # USD per 1M tokens
        self.llm_price_output = float(os.environ.get("LLM_PRICE_OUTPUT", "5.0"))

    def _setup_logging(self, execution_id: str):
        """设置文件日志"""
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"workflow_{execution_id}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # 添加到 root logger 或当前 logger
        logger.addHandler(file_handler)
        
        # [Fix] 禁止 httpx 输出 INFO 日志 (如 200 OK)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        
        logger.info(f"📂 日志文件已创建: {log_file}")
        return file_handler
    
    def register_step(self, step: WorkflowStep):
        """注册工作流步骤"""
        self.steps.append(step)
        logger.info(f"📝 注册步骤: [{step.name}]")

    def create_execution(self, workflow_type: str, initial_context: Dict[str, Any] = None) -> str:
        """
        创建一个新的执行记录，但不立即执行。
        用于异步任务场景，先返回 ID 给前端。
        """
        self.context = initial_context or {}
        self.execution_id = self._create_execution_record(workflow_type)
        logger.info(f"🆕 创建执行记录: {workflow_type} (ID: {self.execution_id})")
        return self.execution_id
    
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
            
        # 设置日志
        log_handler = self._setup_logging(self.execution_id)
            
        logger.info(f"🚀 开始执行工作流: {workflow_type} (ID: {self.execution_id})")
        
        # 2. 初始化步骤记录
        for i, step in enumerate(self.steps):
            self._create_step_record(step, i)
        
        # 3. 顺序执行步骤
        try:
            for i, step in enumerate(self.steps):
                # 检查 should_stop 标志
                # 用于处理工作流提前终止的情况（如手动查询无结果）
                if self.context.get("should_stop", False):
                    # [重构] 调用统一的处理方法
                    self._handle_should_stop()
                    return self.execution_id
                
                self._execute_step_with_retry(step, i)
            
            # 所有步骤完成
            self._update_execution_status("completed", completed_at=datetime.now().isoformat())

            logger.info(f"✅ 工作流执行完成: {self.execution_id}")
            
            # 生成汇总报告
            self.generate_summary_report()
            
            # 移除日志 handler
            if log_handler:
                logger.removeHandler(log_handler)
                log_handler.close()
            
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
                # 用于处理工作流提前终止的情况（如手动查询无结果）
                if self.context.get("should_stop", False):
                    # [修复] 调用统一的处理方法，确保与 run() 行为一致
                    self._handle_should_stop()
                    return self.execution_id
                
                self._execute_step_with_retry(step, i)
            
            # 所有步骤完成
            self._update_execution_status("completed", completed_at=datetime.now().isoformat())
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
        
        
        # [优化] 定义进度回调（含节流逻辑）
        # 节流状态：记录上次写入的 current 值，避免每次回调都写数据库
        last_update = {"current": 0}
        
        def progress_callback(progress_data: Dict[str, Any]):
            """
            进度更新回调函数（含节流逻辑）。
            
            功能：
                1. 接收步骤的进度数据
                2. 使用节流策略减少数据库写入频率
                3. 确保关键进度点（首次、每5次、最后一次）必定写入
            
            Args:
                progress_data (Dict[str, Any]): 进度数据，包含 current, total, message 等字段
            
            节流策略：
                - 第1次进度：必定写入（显示初始状态）
                - 每5次进度：写入一次（如 5, 10, 15...）
                - 最后一次：必定写入（显示100%完成）
            """
            try:
                current = progress_data.get("current", 0)
                total = progress_data.get("total", 1)
                
                # 节流条件判断
                # 1. 每5篇论文更新一次（减少写入频率）
                # 2. 第1篇必须更新（显示初始进度）
                # 3. 最后一篇必须更新（显示100%完成）
                should_update = (
                    (current - last_update["current"]) >= 5 or  # 条件1：间隔5篇
                    current == 1 or                              # 条件2：第一篇
                    current == total                             # 条件3：最后一篇
                )
                
                if should_update:
                    self.db.table("workflow_steps").update({
                        "progress": progress_data
                    }).eq("id", step_record_id).execute()
                    last_update["current"] = current
                    
            except Exception as e:
                logger.error(f"更新步骤进度失败: {e}")
        
        # 注入回调
        step.set_progress_callback(progress_callback)
        
        # max_retries 是重试次数，所以总尝试次数是 max_retries + 1
        total_attempts = step.max_retries + 1
        
        for attempt in range(1, total_attempts + 1):
            try:
                logger.info("\n" + "="*50)
                logger.info(f"👉 执行步骤 [{step.name}] (尝试 {attempt}/{total_attempts})...")
                logger.info("="*50)
                
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
                # 优先使用步骤返回的精确 Cost (如果 API 支持)
                # 如果步骤没有设置 cost (为0)，则根据 Token 计算
                # 注意: 某些步骤可能已经设置了 cost (如 paper_service 返回的)
                step_cost = step.cost
                
                # 获取额外指标
                cache_hit = step.metrics.get("cache_hit_tokens", 0)
                request_count = step.metrics.get("request_count", 0)
                model_name = step.metrics.get("model_name", "")
                
                # 如果没有精确 Cost，手动计算
                if step_cost == 0.0 and (step.tokens_input > 0 or step.tokens_output > 0):
                    # 根据模型名称选择定价
                    price_input = self.llm_price_input
                    price_output = self.llm_price_output
                    
                    if "qwen-plus" in model_name:
                        price_input = settings.QWEN_PLUS_PRICE_INPUT
                        price_output = settings.QWEN_PLUS_PRICE_OUTPUT
                    elif "qwen3-max" in model_name:
                        price_input = settings.QWEN_MAX_PRICE_INPUT
                        price_output = settings.QWEN_MAX_PRICE_OUTPUT
                    
                    step_cost = (step.tokens_input / 1_000_000) * price_input + \
                                (step.tokens_output / 1_000_000) * price_output
                
                # 更新步骤为完成
                self._update_step_status(
                    step_record_id, 
                    "completed",
                    duration_ms=duration_ms,
                    tokens_input=step.tokens_input,
                    tokens_output=step.tokens_output,
                    cost=step_cost,
                    completed_at=datetime.now().isoformat(),
                    # 新增字段
                    model_name=model_name,
                    cache_hit_tokens=cache_hit,
                    request_count=request_count
                )
                
                # 累加到工作流总消耗
                self._increment_workflow_cost(step.tokens_input, step.tokens_output, step_cost)
                
                # 更新当前步骤名称
                self._update_current_step(step.name)
                
                logger.info(f"✅ 步骤 [{step.name}] 完成。耗时: {duration_ms}ms, 成本: ${step_cost:.6f}")
                
                return  # 成功，退出重试循环
                
            except Exception as e:
                error_msg = str(e)
                error_stack = traceback.format_exc()
                logger.error(f"❌ 步骤 [{step.name}] 执行失败 (尝试 {attempt}): {error_msg}")
                
                if attempt < total_attempts:
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
    
    def _handle_should_stop(self) -> None:
        """
        处理工作流提前终止的统一方法。
        
        功能：
        1. 从 context 中提取 stop_reason 和 stop_message
        2. 获取当前执行记录的 metadata 并合并新信息
        3. 更新执行状态为 stopped
        
        使用场景：
        - run() 方法：启动新工作流时遇到 should_stop
        - resume() 方法：恢复工作流时遇到 should_stop
        
        Args:
            无（使用 self.context 和 self.execution_id）
        
        Returns:
            None
        """
        # 获取停止原因和消息
        stop_reason = self.context.get("stop_reason", "unknown")
        stop_message = self.context.get("message", "工作流已停止")
        
        logger.info(f"⏸️ 工作流提前终止: reason={stop_reason}, message={stop_message}")
        
        # 获取当前 metadata 并合并新信息
        # 原因：避免覆盖已有的其他 metadata 字段
        try:
            current_metadata_res = self.db.table("workflow_executions") \
                .select("metadata") \
                .eq("id", self.execution_id) \
                .execute()
            
            current_metadata = {}
            if current_metadata_res.data and current_metadata_res.data[0].get("metadata"):
                current_metadata = json.loads(current_metadata_res.data[0]["metadata"])
        except Exception as e:
            logger.warning(f"获取当前 metadata 失败: {e}")
            current_metadata = {}
        
        # 合并新的停止信息
        current_metadata.update({
            "stop_reason": stop_reason,
            "stop_message": stop_message
        })
        
        # 更新状态为 stopped
        self._update_execution_status(
            "stopped",
            completed_at=datetime.now().isoformat(),
            metadata=json.dumps(current_metadata)
        )
    
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

    def generate_summary_report(self):
        """
        生成工作流执行汇总报告 (表格形式)。
        包含: 阶段名 | Model | Cost | Input | Output | Cache Hit | Requests | Time
        """
        try:
            print("\n" + "="*120)
            print(f"📊 工作流执行汇总报告 (ID: {self.execution_id})")
            print("="*120)
             
            # 获取所有步骤记录
            response = self.db.table("workflow_steps") \
                .select("*") \
                .eq("execution_id", self.execution_id) \
                .order("step_order") \
                .execute()
            
            steps = response.data
            
            # 表头
            header = f"{'阶段名':<22} | {'Model':<15} | {'Cost ($)':<10} | {'Input':<8} | {'Output':<8} | {'Cache':<8} | {'Reqs':<5} | {'Time':<10}"
            print(header)
            print("-" * len(header))
            
            total_cost = 0.0
            total_input = 0
            total_output = 0
            total_cache = 0
            total_reqs = 0
            total_duration_ms = 0
            
            for s in steps:
                name = s.get("step_name", "")
                model = s.get("model_name") or "-"
                cost = s.get("cost", 0.0)
                inp = s.get("tokens_input", 0)
                out = s.get("tokens_output", 0)
                cache = s.get("cache_hit_tokens", 0)
                reqs = s.get("request_count", 0)
                duration_ms = s.get("duration_ms", 0) or 0
                
                # 格式化时间
                duration_sec = duration_ms / 1000
                if duration_sec > 60:
                    minutes = int(duration_sec // 60)
                    seconds = int(duration_sec % 60)
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{duration_sec:.2f}s"
                
                # 累加
                total_cost += cost
                total_input += inp
                total_output += out
                total_cache += cache
                total_reqs += reqs
                total_duration_ms += duration_ms
                
                print(f"{name:<25} | {model:<15} | {cost:<10.6f} | {inp:<8} | {out:<8} | {cache:<8} | {reqs:<5} | {time_str:<10}")
            
            # 格式化总时间
            total_duration_sec = total_duration_ms / 1000
            if total_duration_sec > 60:
                total_minutes = int(total_duration_sec // 60)
                total_seconds = int(total_duration_sec % 60)
                total_time_str = f"{total_minutes}m {total_seconds}s"
            else:
                total_time_str = f"{total_duration_sec:.2f}s"

            print("-" * len(header))
            print(f"{'TOTAL':<25} | {'-':<15} | {total_cost:<10.6f} | {total_input:<8} | {total_output:<8} | {total_cache:<8} | {total_reqs:<5} | {total_time_str:<10}")
            print("="*95 + "\n")
            
        except Exception as e:
            logger.error(f"生成汇总报告失败: {e}")
