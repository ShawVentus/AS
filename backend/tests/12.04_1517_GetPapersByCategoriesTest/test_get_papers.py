import sys
import os
import datetime

# --- 环境配置 ---
# 将项目根目录 (backend) 添加到 python path
# 当前文件: backend/tests/12.04_1517_GetPapersByCategoriesTest/test_get_papers.py
# 目标路径: d:\XWT\AS\backend
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ../.. goes to backend
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
sys.path.insert(0, BACKEND_ROOT) # Insert at beginning
print(f"DEBUG: Added path: {BACKEND_ROOT}")
print(f"DEBUG: sys.path: {sys.path}")

from app.services.paper_service import paper_service

# --- 参数配置 ---
# 测试用的用户 ID
USER_ID = "03985519-8f62-48bb-a3ff-f9bae5481a0f"
# 结果输出路径
RESULT_DIR = os.path.join(CURRENT_DIR, "result")
RESULT_FILE = os.path.join(RESULT_DIR, "test_output.txt")

def test_get_papers_by_categories():
    """
    测试 get_papers_by_categories 函数
    功能：根据用户关注的类别获取候选论文，并同步到私有数据库
    """
    print(f"[{datetime.datetime.now()}] 开始测试 get_papers_by_categories")
    print(f"输入 User ID: {USER_ID}")

    try:
        # 调用被测函数
        # 该函数会内部查询 profiles 获取类别，查询 papers 获取论文，并写入 user_paper_states
        # 返回值是一个日志字符串
        log_output = paper_service.get_papers_by_categories(USER_ID)

        # 打印结果到控制台
        print("\n" + "="*20 + " 执行结果 " + "="*20)
        print(log_output)
        print("="*50 + "\n")

        # 将结果写入文件
        if not os.path.exists(RESULT_DIR):
            os.makedirs(RESULT_DIR)
            
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            f.write(f"测试时间: {datetime.datetime.now()}\n")
            f.write(f"测试函数: get_papers_by_categories\n")
            f.write(f"输入 User ID: {USER_ID}\n")
            f.write("-" * 30 + "\n")
            f.write(f"输出日志:\n{log_output}\n")
            
        print(f"测试结果已保存至: {RESULT_FILE}")

    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_get_papers_by_categories()
