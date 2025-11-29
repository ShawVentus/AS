import sys
import os
import json

# 环境配置
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.abspath(os.path.join(current_dir, "../.."))
sys.path.append(backend_path)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_path, ".env"))

from app.services.paper_service import PaperService
from app.schemas.paper import PersonalizedPaper, RawPaperMetadata
from app.core.database import get_db

def test_analyze_paper():
    # 1. 初始化
    service = PaperService()
    db = get_db()
    
    # 2. 获取待测试论文 (status='completed')
    response = db.table("papers").select("*").eq("status", "completed").limit(1).execute()
    if not response.data:
        print("无 completed 状态论文，测试跳过")
        return
    
    raw_paper = response.data[0]
    print(f"测试论文: {raw_paper['id']}")

    # 3. 构造输入
    links = raw_paper.get("links", {})
    if isinstance(links, str): links = json.loads(links)
    
    meta = RawPaperMetadata(
        id=raw_paper["id"],
        title=raw_paper["title"],
        authors=raw_paper["authors"] or [],
        published_date=raw_paper["published_date"] or "",
        category=raw_paper["category"] or [],
        abstract=raw_paper["abstract"] or "",
        links=links,
        comment=raw_paper.get("comment")
    )
    paper_input = PersonalizedPaper(meta=meta, analysis=None, user_state=None)

    # 4. 执行核心功能
    result = service.analyze_paper(paper_input)

    # 5. 验证结果
    if result:
        print("分析成功")
        # 验证数据库
        updated = db.table("papers").select("status, details").eq("id", raw_paper["id"]).single().execute()
        print(f"新状态: {updated.data['status']}") # 应为 analyzed
        
        # 输出结果到文件
        output_path = os.path.join(current_dir, "result", "test_output.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(updated.data, f, ensure_ascii=False, indent=2)
            print(f"结果已保存: {output_path}")
    else:
        print("分析失败或返回 None")

if __name__ == "__main__":
    test_analyze_paper()
