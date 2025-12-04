import sys
import os
import datetime
import json

# --- 环境配置 ---
# 将项目根目录 (backend) 添加到 python path
# 当前文件: backend/tests/12.04_1603_ProcessPendingPapersTest/test_process_pending.py
# 目标路径: d:\XWT\AS\backend
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
sys.path.insert(0, BACKEND_ROOT)

from app.services.paper_service import paper_service

# --- 参数配置 ---
# 测试用的用户 ID
USER_ID = "03985519-8f62-48bb-a3ff-f9bae5481a0f"
# 结果输出路径
RESULT_DIR = os.path.join(CURRENT_DIR, "result")
RESULT_FILE = os.path.join(RESULT_DIR, "test_output.txt")

def test_process_pending_papers():
    """
    测试 process_pending_papers 函数
    功能：获取用户画像 -> 获取待处理论文 -> 调用 LLM 过滤 -> 返回统计结果
    """
    print(f"[{datetime.datetime.now()}] 开始测试 process_pending_papers")
    print(f"输入 User ID: {USER_ID}")

    try:
        # 调用被测函数
        # 该函数会执行完整的过滤流程，并更新数据库中的 user_paper_states
        response = paper_service.process_pending_papers(USER_ID)

        # 打印结果到控制台
        print("\n" + "="*20 + " 执行结果 " + "="*20)
        print(f"总分析数量: {response.total_analyzed}")
        print(f"接受数量: {response.accepted_count}")
        print(f"拒绝数量: {response.rejected_count}")
        print("="*50 + "\n")

        # 将详细结果写入文件
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR)
            
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            f.write(f"测试时间: {datetime.datetime.now()}\n")
            f.write(f"测试函数: process_pending_papers\n")
            f.write(f"输入 User ID: {USER_ID}\n")
            f.write("-" * 30 + "\n")
            f.write(f"总分析数量: {response.total_analyzed}\n")
            f.write(f"接受数量: {response.accepted_count}\n")
            f.write(f"拒绝数量: {response.rejected_count}\n")
            f.write("-" * 30 + "\n")
            f.write("详细响应内容:\n")
            # 使用 model_dump_json (Pydantic v2) 或 json() (Pydantic v1)
            # 假设是 Pydantic v2
            try:
                f.write(response.model_dump_json(indent=2))
            except AttributeError:
                f.write(response.json(indent=2))
            
        print(f"测试结果已保存至: {RESULT_FILE}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_process_pending_papers()
