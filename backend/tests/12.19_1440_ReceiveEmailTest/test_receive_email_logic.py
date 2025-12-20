#!/usr/bin/env python3
"""
测试文件: test_receive_email_logic.py
主要功能: 验证 receive_email 开关对自动任务用户筛选的影响。
作者: Antigravity
日期: 2025-12-19
"""

import sys
import os

# 将 backend 目录添加到 Python 路径，确保可以导入 app 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.core.database import get_db
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_user_filtering():
    """
    测试用户筛选逻辑。
    
    功能说明：
        对比旧逻辑（仅检查额度）与新逻辑（检查额度 + 接收开关）的筛选结果。
        验证新逻辑是否能正确过滤掉关闭了自动报告的用户。
        
    Args:
        None
        
    Returns:
        None
    """
    db = get_db()
    
    print("=" * 60)
    print("🧪 测试 1: 旧逻辑 - 仅检查额度")
    print("=" * 60)
    
    # 旧逻辑：仅检查额度 (remaining_quota > 0)
    try:
        old_logic = db.table("profiles").select("user_id, remaining_quota, receive_email") \
            .gt("remaining_quota", 0) \
            .execute()
        
        print(f"符合条件用户数: {len(old_logic.data)}")
        for user in old_logic.data[:3]:  # 仅显示前 3 个示例
            print(f"  - 用户ID: {user['user_id']}, 额度: {user['remaining_quota']}, 接收邮件: {user.get('receive_email')}")
    except Exception as e:
        print(f"❌ 旧逻辑测试失败: {e}")
        return

    print("\n" + "=" * 60)
    print("🧪 测试 2: 新逻辑 - 检查额度 + 接收开关")
    print("=" * 60)
    
    # 新逻辑：同时检查额度 (remaining_quota > 0) 和 接收开关 (receive_email = True)
    try:
        new_logic = db.table("profiles").select("user_id, remaining_quota, receive_email") \
            .gt("remaining_quota", 0) \
            .eq("receive_email", True) \
            .execute()
        
        print(f"符合条件用户数: {len(new_logic.data)}")
        for user in new_logic.data[:3]:
            print(f"  - 用户ID: {user['user_id']}, 额度: {user['remaining_quota']}, 接收邮件: {user.get('receive_email')}")
    except Exception as e:
        print(f"❌ 新逻辑测试失败: {e}")
        print("💡 提示: 如果报错 'column receive_email does not exist'，请确保已执行 SQL 迁移脚本。")
        return

    print("\n" + "=" * 60)
    print("📊 测试结果对比")
    print("=" * 60)
    
    old_count = len(old_logic.data)
    new_count = len(new_logic.data)
    filtered_count = old_count - new_count
    
    print(f"旧逻辑筛选出的用户总数: {old_count}")
    print(f"新逻辑筛选出的用户总数: {new_count}")
    print(f"被成功过滤的用户数: {filtered_count} (这些用户关闭了自动报告开关)")
    
    if filtered_count > 0:
        print(f"\n✅ 验证通过: 新逻辑已成功生效，过滤了 {filtered_count} 个用户。")
    elif old_count == new_count and old_count > 0:
        print("\nℹ️  提示: 所有符合额度条件的用户目前都开启了接收开关。")
    elif old_count == 0:
        print("\n⚠️  警告: 数据库中没有额度大于 0 的用户，无法进行对比测试。")
    else:
        print("\n❓ 结果异常，请检查数据库数据。")

if __name__ == "__main__":
    # 创建测试结果输出目录
    result_dir = os.path.join(os.path.dirname(__file__), "result")
    if not os.path.exists(result_dir):
        os.makedirs(result_dir)
        
    test_user_filtering()
