import smtplib
import logging
from typing import List, Dict, Optional, Tuple, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import time
import os
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailSender:
    """
    邮件发送器
    
    主要功能：
    1. 管理 SMTP 连接（支持 SSL/TLS）
    2. 构建 MIME 多部分邮件（HTML + 纯文本）
    3. 发送单封邮件（带重试机制）
    4. 批量发送邮件（带延迟和统计）
    """
    
    def __init__(self):
        """
        初始化邮件发送器
        """
        self.smtp_server = settings.SMTP_SERVER or "smtp.qq.com"
        self.smtp_port = settings.SMTP_PORT
        self.sender_email = settings.SENDER_EMAIL
        self.sender_password = settings.SENDER_PASSWORD
        self.use_ssl = self.smtp_port == 465
        self.timeout = getattr(settings, 'SMTP_TIMEOUT', 30)
        
        # Jinja2环境
        template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def render_template(self, template_name: str, context: Dict) -> str:
        """
        渲染HTML模板
        
        Args:
            template_name (str): 模板文件名
            context (Dict): 模板上下文数据
            
        Returns:
            str: 渲染后的 HTML 字符串
        """
        template = self.env.get_template(template_name)
        return template.render(**context)

    def _create_message(self, to_email: str, subject: str, html_content: str, plain_content: str = None) -> MIMEMultipart:
        """
        创建 MIME 多部分邮件（HTML + 纯文本备选）
        
        Args:
            to_email (str): 收件人邮箱
            subject (str): 邮件主题
            html_content (str): HTML 内容
            plain_content (str, optional): 纯文本内容
            
        Returns:
            MIMEMultipart: 邮件消息对象
        """
        msg = MIMEMultipart('alternative')
        msg['From'] = Header(f'玻尔平台 <{self.sender_email}>')
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')
        
        # 添加纯文本版本（备选）
        if plain_content:
            msg.attach(MIMEText(plain_content, 'plain', 'utf-8'))
        
        # 添加 HTML 版本
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        return msg

    def send_email(self, to_email: str, subject: str, html_content: str, 
                   plain_content: str = None, max_retries: int = 3) -> Tuple[bool, str]:
        """
        发送邮件（带指数退避重试）
        
        Args:
            to_email (str): 收件人邮箱
            subject (str): 邮件主题
            html_content (str): HTML 内容
            plain_content (str, optional): 纯文本内容
            max_retries (int): 最大重试次数
            
        Returns:
            Tuple[bool, str]: (是否成功, 状态消息)
        """
        if not self.sender_email or not self.sender_password:
            logger.error("SMTP凭据未设置")
            return False, "SMTP凭据未设置"

        for attempt in range(1, max_retries + 1):
            try:
                msg = self._create_message(to_email, subject, html_content, plain_content)
                
                server_cls = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP
                logger.debug(f"Attempt {attempt}: Connecting to {self.smtp_server}:{self.smtp_port} (SSL={self.use_ssl})")
                
                with server_cls(self.smtp_server, self.smtp_port, timeout=self.timeout) as server:
                    if not self.use_ssl:
                        server.ehlo()
                        server.starttls()
                        server.ehlo()
                    
                    server.login(self.sender_email, self.sender_password)
                    server.send_message(msg)
                
                logger.info(f"Email sent to {to_email}")
                return True, f"Email sent to {to_email}"
                
            except smtplib.SMTPAuthenticationError:
                error_msg = "SMTP认证失败。请检查邮箱和授权码。"
                logger.error(error_msg)
                return False, error_msg
                
            except Exception as e:
                error_msg = f"发送失败: {str(e)}"
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {error_msg}")
                if attempt < max_retries:
                    time.sleep(attempt) # 指数退避
                else:
                    logger.error(f"已超过最大重试次数 {to_email}")
                    return False, error_msg
        
        return False, "已超过最大重试次数"

    def send_batch_emails(self, recipients: List[str], subject: str, 
                          html_content: str, plain_content: str = None, 
                          delay: float = 1.0, max_retries: int = 1) -> Dict[str, Any]:
        """
        批量发送邮件（带延迟）
        
        Args:
            recipients (List[str]): 收件人列表
            subject (str): 邮件主题
            html_content (str): HTML 内容
            plain_content (str, optional): 纯文本内容
            delay (float): 发送间隔（秒）
            max_retries (int): 单封邮件重试次数
            
        Returns:
            Dict[str, Any]: 发送统计信息
        """
        stats = {
            'total': len(recipients),
            'success': 0,
            'failed': 0,
            'failed_recipients': [],
            'failed_reasons': {}
        }
        
        for i, recipient in enumerate(recipients):
            success, msg = self.send_email(recipient, subject, html_content, plain_content, max_retries)
            if success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
                stats['failed_recipients'].append(recipient)
                stats['failed_reasons'][recipient] = msg
            
            if i < len(recipients) - 1:
                time.sleep(delay)
                
        return stats

email_sender = EmailSender()
