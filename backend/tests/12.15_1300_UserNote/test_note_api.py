import sys
import os
import pytest
from fastapi.testclient import TestClient

# 添加 backend 目录到 sys.path，以便导入 app
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(backend_dir)

from app.main import app
from app.core.auth import get_current_user_id

# --- 测试参数配置 ---
TEST_USER_ID = "test_user_001"
TEST_NOTE_CONTENT = "这是一个测试笔记 - 自动保存验证"
RESULT_DIR = os.path.join(os.path.dirname(__file__), "result")

# --- 模拟认证依赖 ---
def override_get_current_user_id():
    return TEST_USER_ID

app.dependency_overrides[get_current_user_id] = override_get_current_user_id

client = TestClient(app)

def test_user_note_flow():
    """
    测试用户笔记完整流程：
    1. 获取论文列表 (确保有论文可测)
    2. 提交笔记 (API: /feedback)
    3. 验证笔记是否保存成功 (API: /papers/{id})
    """
    print(f"\n[开始测试] 用户笔记功能验证")
    print(f"测试用户: {TEST_USER_ID}")
    
    # 1. 获取论文列表
    response = client.get("/api/v1/papers/")
    if response.status_code != 200:
        print(f"❌ 获取论文列表失败: {response.status_code}")
        # 如果没有论文，尝试 fetch
        print("尝试触发爬虫获取论文...")
        client.post("/api/v1/papers/fetch?limit=1")
        response = client.get("/api/v1/papers/")
    
    papers = response.json()
    if not papers:
        print("❌ 无法获取论文进行测试")
        return

    target_paper = papers[0]
    paper_id = target_paper["meta"]["id"]
    paper_title = target_paper["meta"]["title"]
    print(f"目标论文: {paper_title} (ID: {paper_id})")

    # 2. 提交笔记
    print(f"正在提交笔记: '{TEST_NOTE_CONTENT}'...")
    feedback_data = {
        "note": TEST_NOTE_CONTENT,
        # 同时测试不影响其他字段
        "liked": True 
    }
    
    # 注意：API 路径可能需要根据实际路由调整，假设是 /api/v1/papers/{id}/feedback
    response = client.post(f"/api/v1/papers/{paper_id}/feedback", json=feedback_data)
    
    if response.status_code == 200:
        print("✅ 笔记提交接口调用成功")
    else:
        print(f"❌ 笔记提交失败: {response.status_code} - {response.text}")
        return

    # 3. 验证保存结果
    print("正在验证笔记回显...")
    response = client.get(f"/api/v1/papers/{paper_id}")
    if response.status_code == 200:
        paper_detail = response.json()
        saved_note = paper_detail.get("user_state", {}).get("note")
        saved_liked = paper_detail.get("user_state", {}).get("user_liked")
        
        print(f"读取到的笔记: '{saved_note}'")
        print(f"读取到的Like状态: {saved_liked}")
        
        # 结果记录到文件
        result_file = os.path.join(RESULT_DIR, "test_result.txt")
        with open(result_file, "w") as f:
            f.write(f"Paper ID: {paper_id}\n")
            f.write(f"Expected Note: {TEST_NOTE_CONTENT}\n")
            f.write(f"Actual Note: {saved_note}\n")
            f.write(f"Match: {saved_note == TEST_NOTE_CONTENT}\n")
            
        if saved_note == TEST_NOTE_CONTENT:
            print("✅ 测试通过：笔记内容一致")
        else:
            print("❌ 测试失败：笔记内容不一致")
            
    else:
        print(f"❌ 获取论文详情失败: {response.status_code}")

if __name__ == "__main__":
    # 如果直接运行脚本
    try:
        test_user_note_flow()
    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
