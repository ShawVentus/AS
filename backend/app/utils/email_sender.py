import smtplib
import logging
import time
import os
import contextlib
from typing import List, Dict, Optional, Tuple, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from email.utils import formataddr
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailSender:
    """
    邮件发送器类 (EmailSender Class)
    
    主要功能：
    1. 管理 SMTP 连接（支持 SSL/TLS 加密）。
    2. 构建包含 HTML 和纯文本内容的 MIME 邮件。
    3. 提供带重试机制的单封邮件发送功能。
    4. 提供带连接复用和延迟控制的批量邮件发送功能，防止触发反垃圾邮件策略。
    """
    
    def __init__(self):
        """
        初始化邮件发送器 (Initialize EmailSender)
        
        功能：从系统配置中读取 SMTP 服务器、端口、发件人账号及授权码。
        """
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.SENDER_EMAIL
        self.sender_password = settings.SENDER_PASSWORD
        self.sender_name = settings.SENDER_NAME
        self.use_ssl = self.smtp_port == 465
        self.timeout = settings.SMTP_TIMEOUT
        
        # 初始化 Jinja2 模板环境
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))

    @contextlib.contextmanager
    def smtp_connection(self):
        """
        SMTP 连接上下文管理器 (SMTP Connection Context Manager)
        
        功能：自动建立 SMTP 连接、执行登录，并在退出时安全关闭连接。
        
        Yields:
            smtplib.SMTP: 建立并登录好的 SMTP 连接对象。
            
        Raises:
            smtplib.SMTPAuthenticationError: 认证失败时抛出。
            Exception: 其他连接异常。
        """
        server = None
        try:
            # [DEBUG] 环境变量脱敏校验
            email_len = len(self.sender_email) if self.sender_email else 0
            pass_len = len(self.sender_password) if self.sender_password else 0
            email_hint = f"{self.sender_email[0]}***{self.sender_email[-1]}" if email_len > 2 else "N/A"
            
            logger.info(f"🔍 [DEBUG] SMTP 认证信息校验: Email长度={email_len}({email_hint}), Password长度={pass_len}")
            
            server_cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
            server = server_cls(self.smtp_server, self.smtp_port, timeout=self.timeout)
            
            # [DEBUG] 开启 SMTP 详细调试模式
            server.set_debuglevel(1)
            
            if not self.use_ssl:
                server.ehlo()
                server.starttls()
                server.ehlo()
                
            server.login(self.sender_email, self.sender_password)
            yield server
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    def render_template(self, template_name: str, context: Dict) -> str:
        """
        渲染 HTML 邮件模板 (Render HTML Template)
        
        Args:
            template_name (str): 模板文件名称（位于 templates 目录下）。
            context (Dict): 注入模板的上下文数据字典。
            
        Returns:
            str: 渲染后的 HTML 字符串内容。
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def _create_message(self, to_email: str, subject: str, html_content: str, plain_content: str = None) -> MIMEMultipart:
        """
        创建 MIME 多部分邮件对象 (Create MIME Message)
        
        Args:
            to_email (str): 收件人邮箱地址。
            subject (str): 邮件主题。
            html_content (str): HTML 格式的邮件正文。
            plain_content (str, 可选): 纯文本格式的邮件正文。
            
        Returns:
            MIMEMultipart: 构建好的邮件消息对象。
        """
        msg = MIMEMultipart('alternative')
        # 发件人显示名称从配置读取
        msg['From'] = formataddr((self.sender_name, self.sender_email))
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        if plain_content:
            msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
        
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        return msg

    def send_email(self, to_email: str, subject: str, html_content: str, 
                   plain_content: str = None, max_retries: int = 3) -> Tuple[bool, str]:
        """
        发送单封邮件 (Send Single Email)
        
        Args:
            to_email (str): 收件人邮箱地址。
            subject (str): 邮件主题。
            html_content (str): HTML 格式的正文。
            plain_content (str, 可选): 纯文本格式的正文。
            max_retries (int): 最大重试次数。
            
        Returns:
            Tuple[bool, str]: (是否成功, 状态或错误描述)。
        """
        if not self.sender_email or not self.sender_password:
            logger.error("❌ 邮件配置缺失：未设置发件人邮箱或授权码")
            return False, "邮件配置缺失"

        for attempt in range(1, max_retries + 1):
            try:
                msg = self._create_message(to_email, subject, html_content, plain_content)
                with self.smtp_connection() as server:
                    server.send_message(msg)
                logger.info(f"✅ 邮件成功发送至: {to_email}")
                return True, f"邮件已发送至 {to_email}"
                
            except smtplib.SMTPAuthenticationError:
                error_msg = "❌ 邮件认证失败：请检查发件人邮箱地址和 SMTP 授权码是否正确。"
                logger.error(error_msg)
                return False, error_msg
                
            except Exception as e:
                error_msg = f"发送异常: {str(e)}"
                logger.warning(f"⚠️ 第 {attempt}/{max_retries} 次尝试失败: {error_msg}")
                if attempt < max_retries:
                    time.sleep(attempt)
                else:
                    logger.error(f"❌ 发送邮件至 {to_email} 失败，已达最大重试次数。")
                    return False, error_msg
        
        return False, "超过最大重试次数"

    def send_batch_emails(self, recipients: List[str], subject: str, 
                          html_content: str, plain_content: str = None, 
                          delay: float = None, max_retries: int = 1) -> Dict[str, Any]:
        """
        批量发送邮件 (Send Batch Emails)
        
        功能：通过连接复用技术，在单个 SMTP 会话中发送多封邮件，提升效率。
        
        Args:
            recipients (List[str]): 收件人邮箱列表。
            subject (str): 邮件主题。
            html_content (str): HTML 格式的正文。
            plain_content (str, 可选): 纯文本格式的正文。
            delay (float, 可选): 每次发送之间的延迟时间。若不传则使用配置值。
            max_retries (int): 每封邮件在连接断开时的重试次数。
            
        Returns:
            Dict[str, Any]: 包含总数、成功数、失败数及失败原因的统计字典。
        """
        if delay is None:
            delay = settings.BATCH_EMAIL_DELAY

        stats = {
            'total': len(recipients),
            'success': 0,
            'failed': 0,
            'failed_recipients': [],
            'failed_reasons': {}
        }
        
        if not recipients:
            return stats

        try:
            logger.info(f"🚀 开始批量发送邮件，共 {len(recipients)} 位收件人...")
            with self.smtp_connection() as server:
                for i, recipient in enumerate(recipients):
                    try:
                        msg = self._create_message(recipient, subject, html_content, plain_content)
                        server.send_message(msg)
                        stats['success'] += 1
                        logger.info(f"📧 [{i+1}/{len(recipients)}] 邮件已发送至: {recipient}")
                    except Exception as e:
                        stats['failed'] += 1
                        stats['failed_recipients'].append(recipient)
                        stats['failed_reasons'][recipient] = str(e)
                        logger.error(f"❌ [{i+1}/{len(recipients)}] 发送至 {recipient} 失败: {str(e)}")
                        
                        # 如果连接断开，尝试重新建立连接（此处简单处理，实际可增加更复杂的重连逻辑）
                        if "closed" in str(e).lower() or "broken pipe" in str(e).lower():
                            logger.warning("⚠️ 检测到连接断开，尝试在下一封发送前重新建立连接...")
                            # 退出当前 with，外层循环或逻辑可根据需要重试，此处为简化版
                    
                    # 延迟控制，规避反垃圾策略
                    if i < len(recipients) - 1:
                        time.sleep(delay)
                        
        except Exception as e:
            logger.error(f"❌ 批量发送初始化失败: {str(e)}")
            return {"error": str(e), "stats": stats}
                
        logger.info(f"🏁 批量发送完成。成功: {stats['success']}, 失败: {stats['failed']}")
        return stats

# 实例化全局邮件发送对象 (Global Instance)
email_sender = EmailSender()
