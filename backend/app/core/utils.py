"""
utils.py
通用工具函数模块。
"""

from datetime import datetime
import re
import logging

logger = logging.getLogger(__name__)

def parse_arxiv_date(date_str: str) -> str:
    """
    解析 ArXiv 日期字符串并转换为 ISO 格式 (YYYY-MM-DD)。
    
    支持格式：
    1. ArXiv 格式: "Monday, 16 December 2025"
    2. ISO 格式: "2025-12-16"
    
    如果解析失败，返回当前日期 (ISO 格式)。
    
    Args:
        date_str (str): 日期字符串
        
    Returns:
        str: ISO 格式日期字符串
    """
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
        
    # 1. 检查是否已经是 ISO 格式
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return date_str
        
    # 2. 尝试解析 ArXiv 格式
    try:
        parsed_date = datetime.strptime(date_str, "%A, %d %B %Y")
        return parsed_date.strftime("%Y-%m-%d")
    except ValueError:
        pass
        
    # 3. 尝试其他常见格式 (可选)
    
    # 4. 解析失败，记录警告并返回当前日期
    logger.warning(f"无法解析日期 '{date_str}'，使用当前日期作为 fallback")
    return datetime.now().strftime("%Y-%m-%d")
