import os
import sys
from dotenv import load_dotenv

# 将 backend 目录添加到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.user_service import user_service

def test_quota_system():
    """
    测试用户额度系统的核心逻辑。
    
    注意：此测试会直接操作数据库，请确保使用测试账号或在开发环境运行。
    """
    # 1. 准备测试用户 ID (请确保此用户在 profiles 表中存在)
    # 我们可以尝试获取当前系统中的第一个用户
    try:
        profiles = user_service.db.table("profiles").select("user_id, info").limit(1).execute()
        if not profiles.data:
            print("❌ 数据库中没有用户，请先创建用户")
            return
        
        test_user_id = profiles.data[0]["user_id"]
        user_name = profiles.data[0]["info"].get("name", "未知用户")
        print(f"🔍 开始测试用户: {user_name} ({test_user_id})")
        
        # 2. 测试获取初始额度
        initial_quota = user_service.get_remaining_quota(test_user_id)
        print(f"📊 初始额度: {initial_quota}")
        
        # 3. 测试增加额度
        print("➕ 正在增加 5 个额度...")
        user_service.add_quota(test_user_id, 5, reason="test_grant")
        new_quota = user_service.get_remaining_quota(test_user_id)
        print(f"📊 增加后额度: {new_quota}")
        assert new_quota == initial_quota + 5
        
        # 4. 测试额度充足性校验
        print("⚖️ 检查额度是否充足 (需要 3 个)...")
        has_enough = user_service.has_sufficient_quota(test_user_id, 3)
        print(f"结果: {'充足' if has_enough else '不足'}")
        assert has_enough is True
        
        # 5. 测试扣减额度
        print("➖ 正在扣减 2 个额度...")
        success = user_service.deduct_quota(test_user_id, 2, reason="test_deduction")
        final_quota = user_service.get_remaining_quota(test_user_id)
        print(f"📊 扣减后额度: {final_quota}")
        assert success is True
        assert final_quota == new_quota - 2
        
        # 6. 测试额度不足时的扣减
        print("🚫 尝试扣减超过剩余数量的额度 (100 个)...")
        fail_success = user_service.deduct_quota(test_user_id, 100, reason="test_overdraw")
        print(f"结果: {'成功 (异常)' if fail_success else '失败 (符合预期)'}")
        assert fail_success is False
        
        print("\n✅ 所有 Service 层逻辑测试通过！")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 加载环境变量
    load_dotenv()
    test_quota_system()
