"""
error_notifier.py
错误邮件通知工具类

主要功能：
1. 提供统一的错误邮件发送接口
2. 实现智能限流机制，避免邮件轰炸
3. 自动过滤敏感信息（API Key等）
4. 支持错误分级和上下文信息记录
5. 防止递归错误（邮件发送失败不再发送邮件）
"""

import os
import re
import time
import logging
import traceback
from typing import Dict, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
from app.core.config import settings
from app.utils.email_sender import email_sender

logger = logging.getLogger(__name__)


class ErrorNotifier:
    """
    错误邮件通知器
    
    功能说明：
        为系统提供统一的错误通知能力，支持智能限流和敏感信息过滤。
        通过限流机制避免相同错误重复发送邮件，防止邮件轰炸。
        
    主要特性：
        - 智能限流：同类错误在冷却时间内只发送一次
        - 频率控制：每小时最多发送指定数量的错误邮件
        - 敏感信息过滤：自动替换API Key、密码等敏感字段
        - 环境控制：开发环境可选择不发送真实邮件
        - 防递归：邮件发送失败只记录日志，不再发送通知
    """
    
    def __init__(self):
        """
        初始化错误通知器
        
        功能：
            从配置中加载错误邮件设置，初始化限流记录。
        """
        self.notification_email = settings.ERROR_NOTIFICATION_EMAIL
        self.enabled = settings.ENABLE_ERROR_NOTIFICATIONS
        self.cooldown_seconds = settings.ERROR_NOTIFICATION_COOLDOWN
        self.max_per_hour = settings.ERROR_NOTIFICATION_MAX_PER_HOUR
        
        # 限流状态跟踪
        # 记录每种错误类型的最后发送时间，用于实现冷却机制
        self._last_sent: Dict[str, float] = {}
        
        # 记录每小时的发送计数，用于控制总发送频率
        self._hourly_count: Dict[str, int] = defaultdict(int)
        self._current_hour: str = self._get_current_hour()
        
        logger.info(f"错误通知器已初始化 - 启用状态: {self.enabled}, 通知邮箱: {self.notification_email}")
    
    def _get_current_hour(self) -> str:
        """
        获取当前小时标识
        
        功能：
            生成格式为 "YYYY-MM-DD-HH" 的时间标识，用于按小时统计邮件数量。
        
        Returns:
            str: 小时标识字符串，例如 "2025-12-18-14"
        """
        return datetime.now().strftime("%Y-%m-%d-%H")
    
    def _check_cooldown(self, error_type: str) -> bool:
        """
        检查错误类型是否在冷却期内
        
        功能：
            判断指定类型的错误距离上次发送邮件是否已超过冷却时间。
            如果还在冷却期内，则跳过本次发送。
        
        Args:
            error_type (str): 错误类型标识，如 "WORKFLOW_FAILED"
        
        Returns:
            bool: True表示可以发送（已过冷却期），False表示仍在冷却期
        """
        if error_type not in self._last_sent:
            return True
        
        time_since_last = time.time() - self._last_sent[error_type]
        return time_since_last >= self.cooldown_seconds
    
    def _check_hourly_limit(self) -> bool:
        """
        检查当前小时是否已达发送上限
        
        功能：
            检查当前小时已发送的错误邮件数量是否超过配置的上限。
            如果超过限制，则跳过本次发送。
            每小时开始时自动重置计数器。
        
        Returns:
            bool: True表示未达上限可以发送，False表示已达上限
        """
        current_hour = self._get_current_hour()
        
        # 如果进入新的小时，重置计数器
        if current_hour != self._current_hour:
            self._current_hour = current_hour
            self._hourly_count.clear()
        
        return self._hourly_count[current_hour] < self.max_per_hour
    
    def _filter_sensitive_info(self, text: str) -> str:
        """
        过滤文本中的敏感信息
        
        功能：
            使用正则表达式匹配并替换常见的敏感信息，如API Key、密码、邮箱等。
            保护系统安全，避免敏感信息通过错误邮件泄露。
        
        Args:
            text (str): 需要过滤的原始文本（如错误堆栈、上下文信息）
        
        Returns:
            str: 过滤后的安全文本
        """
        if not text:
            return text
        
        # 过滤API Key（通常是长字符串）
        text = re.sub(r'(api[_-]?key["\']?\s*[:=]\s*["\']?)[\w-]{20,}(["\']?)', r'\1***FILTERED***\2', text, flags=re.IGNORECASE)
        
        # 过滤密码字段
        text = re.sub(r'(password["\']?\s*[:=]\s*["\']?)[^\s"\']+(["\']?)', r'\1***FILTERED***\2', text, flags=re.IGNORECASE)
        
        # 过滤邮箱地址（保留域名）
        text = re.sub(r'\b([a-zA-Z0-9])[a-zA-Z0-9._-]*@', r'\1***@', text)
        
        # 过滤Bearer Token
        text = re.sub(r'Bearer\s+[\w-]+', 'Bearer ***FILTERED***', text, flags=re.IGNORECASE)
        
        return text
    
    def _format_error_email(
        self, 
        error_type: str, 
        error_message: str, 
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None,
        severity: str = "CRITICAL"
    ) -> tuple[str, str]:
        """
        格式化错误邮件内容
        
        功能：
            根据错误信息生成结构化的邮件主题和正文。
            自动过滤敏感信息，添加时间、严重级别等元数据。
        
        Args:
            error_type (str): 错误类型，如 "WORKFLOW_FAILED", "CRAWLER_FAILED"
            error_message (str): 错误描述信息
            context (Optional[Dict]): 错误上下文信息，如 user_id, execution_id 等
            stack_trace (Optional[str]): 错误堆栈追踪信息
            severity (str): 严重级别，可选值: "CRITICAL"(严重), "WARNING"(警告), "INFO"(信息)
        
        Returns:
            tuple[str, str]: (邮件主题, 邮件正文)
        """
        # 严重级别对应的emoji和中文描述
        severity_map = {
            "CRITICAL": ("🔴", "严重"),
            "WARNING": ("🟡", "警告"),
            "INFO": ("🔵", "信息")
        }
        emoji, severity_cn = severity_map.get(severity, ("⚠️", "未知"))
        
        # 构建邮件主题
        subject = f"【ArxivScout 错误告警】{emoji} {error_type}"
        
        # 过滤敏感信息
        safe_message = self._filter_sensitive_info(error_message)
        safe_trace = self._filter_sensitive_info(stack_trace) if stack_trace else ""
        
        # 构建邮件正文
        content = f"""【ArxivScout 系统错误告警】

错误类型: {error_type}
发生时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (UTC+8)
严重级别: {emoji} {severity_cn}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
错误摘要:
{safe_message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # 添加上下文信息（如果有）
        if context:
            content += "\n详细信息:\n"
            for key, value in context.items():
                safe_value = self._filter_sensitive_info(str(value))
                content += f"  - {key}: {safe_value}\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # 添加堆栈追踪（如果有）
        if safe_trace:
            content += f"\n堆栈追踪:\n{safe_trace}\n"
            content += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # 添加邮件尾部
        content += f"""
此邮件由 ArxivScout 系统自动发送
同类错误在 {self.cooldown_seconds // 60} 分钟内不会重复发送

---
如需查看完整日志，请登录服务器
"""
        
        return subject, content
    
    def notify_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None,
        severity: str = "CRITICAL"
    ) -> bool:
        """
        发送错误通知邮件（主要接口）
        
        功能：
            系统各模块调用此方法发送错误通知。
            内部会自动进行限流检查、敏感信息过滤、邮件格式化等处理。
        
        Args:
            error_type (str): 错误类型标识，建议使用大写下划线格式，如:
                - "WORKFLOW_FAILED": 工作流执行失败
                - "CRAWLER_FAILED": 爬虫执行失败
                - "REPORT_GENERATION_FAILED": 报告生成失败
                - "LLM_API_FAILED": LLM API调用失败
            error_message (str): 错误的详细描述信息
            context (Optional[Dict]): 错误相关的上下文信息，建议包含:
                - user_id: 用户ID（如果相关）
                - execution_id: 执行ID（工作流场景）
                - paper_id: 论文ID（论文处理场景）
                等其他有助于排查问题的信息
            stack_trace (Optional[str]): Python异常的堆栈追踪，可通过 traceback.format_exc() 获取
            severity (str): 严重级别，默认为 "CRITICAL"
                - "CRITICAL": 严重错误，影响核心功能
                - "WARNING": 警告级别，部分功能受影响但可继续
                - "INFO": 信息级别，仅供参考
        
        Returns:
            bool: 是否成功发送通知邮件
                - True: 邮件发送成功
                - False: 未发送（被限流、未启用、发送失败等）
        
        使用示例:
            ```python
            try:
                # 业务逻辑
                run_crawler()
            except Exception as e:
                error_notifier.notify_error(
                    error_type="CRAWLER_FAILED",
                    error_message=f"爬虫执行失败: {str(e)}",
                    context={"execution_id": execution_id},
                    stack_trace=traceback.format_exc(),
                    severity="CRITICAL"
                )
            ```
        """
        # 检查是否启用错误通知
        if not self.enabled:
            logger.info(f"错误通知已禁用，跳过发送: {error_type}")
            return False
        
        # 检查是否配置了通知邮箱
        if not self.notification_email:
            logger.warning("未配置错误通知邮箱(ERROR_NOTIFICATION_EMAIL)，跳过发送")
            return False
        
        # 开发环境特殊处理（可选）
        environment = os.getenv("ENVIRONMENT", "production")
        if environment == "development":
            logger.warning(f"[开发环境 - 模拟发送错误邮件] 类型: {error_type}")
            logger.warning(f"[错误信息] {error_message}")
            if context:
                logger.warning(f"[上下文] {context}")
            return True
        
        # 检查限流条件
        if not self._check_cooldown(error_type):
            cooldown_remaining = self.cooldown_seconds - (time.time() - self._last_sent[error_type])
            logger.info(f"错误类型 '{error_type}' 仍在冷却期，剩余 {int(cooldown_remaining)} 秒，跳过发送")
            return False
        
        if not self._check_hourly_limit():
            logger.warning(f"当前小时({self._current_hour})已达错误邮件发送上限({self.max_per_hour}封)，跳过发送")
            return False
        
        # 格式化邮件内容
        subject, content = self._format_error_email(
            error_type=error_type,
            error_message=error_message,
            context=context,
            stack_trace=stack_trace,
            severity=severity
        )
        
        # 发送邮件（捕获异常防止递归错误）
        try:
            success, message = email_sender.send_email(
                to_email=self.notification_email,
                subject=subject,
                html_content=f"<pre>{content}</pre>",  # 使用pre标签保持格式
                plain_content=content,
                max_retries=2  # 错误邮件重试次数设置较少，避免阻塞
            )
            
            if success:
                # 更新限流状态
                self._last_sent[error_type] = time.time()
                self._hourly_count[self._current_hour] += 1
                logger.info(f"✅ 错误通知邮件已发送: {error_type} -> {self.notification_email}")
                return True
            else:
                # 邮件发送失败，只记录日志，不再发送通知（防止递归）
                logger.error(f"❌ 错误通知邮件发送失败: {message}")
                return False
                
        except Exception as e:
            # 捕获所有异常，防止错误通知本身导致系统崩溃
            logger.error(f"❌ 发送错误通知时发生异常: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def notify_critical_error(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None
    ) -> bool:
        """
        发送严重级别错误通知（便捷方法）
        
        功能：
            等同于调用 notify_error(..., severity="CRITICAL")
            用于快速发送严重错误通知，代码更简洁。
        
        Args:
            error_type (str): 错误类型标识
            error_message (str): 错误描述
            context (Optional[Dict]): 上下文信息
            stack_trace (Optional[str]): 堆栈追踪
        
        Returns:
            bool: 是否成功发送
        """
        return self.notify_error(
            error_type=error_type,
            error_message=error_message,
            context=context,
            stack_trace=stack_trace,
            severity="CRITICAL"
        )
    
    def notify_warning(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict] = None,
        stack_trace: Optional[str] = None
    ) -> bool:
        """
        发送警告级别错误通知（便捷方法）
        
        功能：
            等同于调用 notify_error(..., severity="WARNING")
            用于发送非致命但需要关注的警告信息。
        
        Args:
            error_type (str): 错误类型标识
            error_message (str): 错误描述
            context (Optional[Dict]): 上下文信息
            stack_trace (Optional[str]): 堆栈追踪
        
        Returns:
            bool: 是否成功发送
        """
        return self.notify_error(
            error_type=error_type,
            error_message=error_message,
            context=context,
            stack_trace=stack_trace,
            severity="WARNING"
        )


# 全局单例实例
error_notifier = ErrorNotifier()
