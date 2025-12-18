"""
RLS 启用后表写入测试

测试目标：
    验证启用 RLS 后，使用 Service Key 是否能正常写入以下表：
    - email_analytics
    - system_logs
    - report_feedback

主要功能：
    1. 测试写入 email_analytics（邮件分析）
    2. 测试写入 system_logs（系统日志）
    3. 测试写入 report_feedback（报告反馈）
    4. 测试删除插入的数据（清理）
"""

import os
import sys
import uuid
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.core.database import get_db

# ==================== 参数配置 ====================
TEST_USER_ID = "test_user_rls_001"
# TEST_REPORT_ID 将在创建 report 后动态获取
RESULT_FILE = os.path.join(os.path.dirname(__file__), "result", "test_result.txt")

# ==================== 工具函数 ====================

def log_result(message: str, success: bool = True):
    """
    记录测试结果到文件和控制台
    
    Args:
        message (str): 日志消息
        success (bool): 是否成功
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅" if success else "❌"
    log_line = f"[{timestamp}] {status} {message}\n"
    
    print(log_line.strip())
    
    # 确保 result 目录存在
    os.makedirs(os.path.dirname(RESULT_FILE), exist_ok=True)
    
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(log_line)


def create_test_report():
    """
    创建测试用的 report 记录（用于满足外键约束）
    
    Returns:
        tuple: (是否成功, report_id)
    """
    db = get_db()
    
    try:
        log_result("创建测试 report 记录...")
        
        # 创建测试数据
        test_report = {
            "id": str(uuid.uuid4()),
            "user_id": TEST_USER_ID,
            "email": "test@example.com",
            "title": "RLS 测试报告",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "summary": "这是一个用于测试 RLS 的报告",
            "content": "测试内容",
            "ref_papers": [],
            "total_papers_count": 0,
            "recommended_papers_count": 0,
            "created_at": datetime.now().isoformat()
        }
        
        result = db.table("reports").insert(test_report).execute()
        
        if result.data:
            report_id = result.data[0]["id"]
            log_result(f"测试 report 创建成功，ID: {report_id}", True)
            return True, report_id
        else:
            log_result("测试 report 创建失败：未返回数据", False)
            return False, None
            
    except Exception as e:
        log_result(f"测试 report 创建异常: {str(e)}", False)
        return False, None


def test_email_analytics(report_id: str):
    """
    测试 email_analytics 表写入
    
    Returns:
        tuple: (是否成功, 记录ID)
    """
    db = get_db()
    
    try:
        log_result("开始测试 email_analytics 表...")
        
        # 插入测试数据
        test_data = {
            "report_id": report_id,
            "user_id": TEST_USER_ID,
            "event_type": "sent",
            "event_data": {"test": True, "stats": {"count": 10}}
        }
        
        result = db.table("email_analytics").insert(test_data).execute()
        
        if result.data:
            record_id = result.data[0]["id"]
            log_result(f"email_analytics 写入成功，ID: {record_id}", True)
            return True, record_id
        else:
            log_result("email_analytics 写入失败：未返回数据", False)
            return False, None
            
    except Exception as e:
        log_result(f"email_analytics 写入异常: {str(e)}", False)
        return False, None


def test_system_logs():
    """
    测试 system_logs 表写入
    
    Returns:
        tuple: (是否成功, 记录ID)
    """
    db = get_db()
    
    try:
        log_result("开始测试 system_logs 表...")
        
        # 插入测试数据
        test_data = {
            "level": "INFO",
            "source": "test_script",
            "message": "RLS 启用后测试日志写入",
            "meta": {"test": True, "timestamp": datetime.now().isoformat()}
        }
        
        result = db.table("system_logs").insert(test_data).execute()
        
        if result.data:
            record_id = result.data[0]["id"]
            log_result(f"system_logs 写入成功，ID: {record_id}", True)
            return True, record_id
        else:
            log_result("system_logs 写入失败：未返回数据", False)
            return False, None
            
    except Exception as e:
        log_result(f"system_logs 写入异常: {str(e)}", False)
        return False, None


def test_report_feedback(report_id: str):
    """
    测试 report_feedback 表写入
    
    Returns:
        tuple: (是否成功, 记录ID)
    """
    db = get_db()
    
    try:
        log_result("开始测试 report_feedback 表...")
        
        # 插入测试数据
        test_data = {
            "report_id": report_id,
            "user_id": TEST_USER_ID,
            "rating": 5,
            "feedback_text": "RLS 启用后测试反馈功能"
        }
        
        result = db.table("report_feedback").insert(test_data).execute()
        
        if result.data:
            record_id = result.data[0]["id"]
            log_result(f"report_feedback 写入成功，ID: {record_id}", True)
            return True, record_id
        else:
            log_result("report_feedback 写入失败：未返回数据", False)
            return False, None
            
    except Exception as e:
        log_result(f"report_feedback 写入异常: {str(e)}", False)
        return False, None


def cleanup_test_data(report_id: str = None,
                      email_analytics_id: str = None, 
                      system_logs_id: str = None, 
                      report_feedback_id: str = None):
    """
    清理测试数据
    
    Args:
        report_id (str): 测试 report ID
        email_analytics_id (str): email_analytics 记录ID
        system_logs_id (str): system_logs 记录ID
        report_feedback_id (str): report_feedback 记录ID
    """
    db = get_db()
    log_result("开始清理测试数据...")
    
    try:
        if email_analytics_id:
            db.table("email_analytics").delete().eq("id", email_analytics_id).execute()
            log_result(f"已删除 email_analytics 记录: {email_analytics_id}", True)
    except Exception as e:
        log_result(f"删除 email_analytics 记录失败: {str(e)}", False)
    
    try:
        if system_logs_id:
            db.table("system_logs").delete().eq("id", system_logs_id).execute()
            log_result(f"已删除 system_logs 记录: {system_logs_id}", True)
    except Exception as e:
        log_result(f"删除 system_logs 记录失败: {str(e)}", False)
    
    try:
        if report_feedback_id:
            db.table("report_feedback").delete().eq("id", report_feedback_id).execute()
            log_result(f"已删除 report_feedback 记录: {report_feedback_id}", True)
    except Exception as e:
        log_result(f"删除 report_feedback 记录失败: {str(e)}", False)
    
    try:
        if report_id:
            db.table("reports").delete().eq("id", report_id).execute()
            log_result(f"已删除 reports 记录: {report_id}", True)
    except Exception as e:
        log_result(f"删除 reports 记录失败: {str(e)}", False)


def main():
    """
    主测试流程
    """
    log_result("=" * 60)
    log_result("RLS 启用后表写入测试开始")
    log_result("=" * 60)
    
    # 清空之前的测试结果文件
    if os.path.exists(RESULT_FILE):
        os.remove(RESULT_FILE)
    
    # 先创建测试 report（满足外键约束）
    report_ok, test_report_id = create_test_report()
    
    if not report_ok:
        log_result("无法创建测试 report，终止测试", False)
        return
    
    # 执行测试
    email_success, email_id = test_email_analytics(test_report_id)
    log_success, log_id = test_system_logs()
    feedback_success, feedback_id = test_report_feedback(test_report_id)
    
    log_result("=" * 60)
    
    # 汇总结果
    total_tests = 3
    passed_tests = sum([email_success, log_success, feedback_success])
    
    log_result(f"测试完成: {passed_tests}/{total_tests} 通过")
    
    if passed_tests == total_tests:
        log_result("🎉 所有测试通过！RLS 启用后 Service Key 可正常写入", True)
    else:
        log_result("⚠️  部分测试失败，请检查 RLS 配置或 Service Key 设置", False)
    
    log_result("=" * 60)
    
    # 询问是否清理数据
    cleanup_choice = input("\n是否清理测试数据？(y/n): ").strip().lower()
    if cleanup_choice == 'y':
        cleanup_test_data(test_report_id, email_id, log_id, feedback_id)
        log_result("测试数据已清理")
    else:
        log_result("测试数据保留，可在数据库中手动查看")
        log_result(f"  - report ID: {test_report_id}")
        log_result(f"  - email_analytics ID: {email_id}")
        log_result(f"  - system_logs ID: {log_id}")
        log_result(f"  - report_feedback ID: {feedback_id}")
    
    log_result(f"\n测试结果已保存到: {RESULT_FILE}")


if __name__ == "__main__":
    main()
