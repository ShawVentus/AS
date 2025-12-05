import sys
import os
import time

# --- 参数配置 (Parameters) ---
# 添加 backend 目录到 python path，确保能导入 app 模块
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(BACKEND_DIR)

from app.services.scheduler import SchedulerService

def test_process_personalized_papers():
    """
    测试 process_personalized_papers 函数。
    
    功能：
    1. 初始化调度器服务。
    2. 调用 process_personalized_papers 执行个性化筛选逻辑。
    3. 该函数会直接与 Supabase 交互：
       - 读取 daily_papers (今日论文)
       - 读取 profiles (用户画像)
       - 读取 user_paper_states (用户历史状态)
       - 调用 LLM 进行筛选 (paper_service.filter_papers)
       - 更新 user_paper_states (写入筛选结果)
    
    预期输出：
    - 控制台打印处理日志，包括每个用户待处理的论文数量。
    - Supabase 中的 user_paper_states 表应新增相应的记录。
    """
    print(f"开始测试: process_personalized_papers")
    print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 初始化服务
        scheduler = SchedulerService()
        
        # 2. 执行核心功能
        # 注意：这将触发真实的 LLM 调用和数据库写入
        scheduler.process_personalized_papers()
        
        print("\n测试执行完成。")
        print("请检查 Supabase 的 'user_paper_states' 表以验证字段是否更新。")
        
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        raise e

if __name__ == "__main__":
    test_process_personalized_papers()
