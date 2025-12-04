import sys
import os
import json

# 添加项目根目录到 python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
sys.path.insert(0, BACKEND_ROOT)

from app.core.database import get_db

USER_ID = "03985519-8f62-48bb-a3ff-f9bae5481a0f"

def debug_database():
    """调试数据库数据"""
    db = get_db()

    print("\n" + "="*50)
    print("1. 查询用户的 user_paper_states 数据")
    print("="*50)
    result = db.table('user_paper_states').select('*').eq('user_id', USER_ID).limit(5).execute()
    print(f"找到 {len(result.data) if result.data else 0} 条记录")
    if result.data:
        for item in result.data:
            print(f"\n论文ID: {item.get('paper_id')}")
            print(f"  why_this_paper: {item.get('why_this_paper')}")
            print(f"  relevance_score: {item.get('relevance_score')}")
            print(f"  accepted: {item.get('accepted')}")
            print(f"  created_at: {item.get('created_at')}")

    print("\n" + "="*50)
    print("2. 查询用户的 Profile 数据")
    print("="*50)
    profile_result = db.table('profiles').select('*').eq('user_id', USER_ID).execute()
    if profile_result.data:
        profile = profile_result.data[0]
        print(f"Focus categories: {profile.get('focus', {}).get('category', [])}")
        print(f"Full focus: {json.dumps(profile.get('focus', {}), indent=2, ensure_ascii=False)}")

    print("\n" + "="*50)
    print("3. 查询 papers 表中的论文数据（按类别）")
    print("="*50)

    # 获取用户关注的类别
    if profile_result.data:
        categories = profile_result.data[0].get('focus', {}).get('category', [])
        print(f"用户关注的类别: {categories}")

        if categories:
            # 查询符合类别的论文
            papers_result = db.table('papers').select('id, title, category').overlaps('category', categories).limit(10).execute()
            print(f"\n找到 {len(papers_result.data) if papers_result.data else 0} 篇符合类别的论文")

            # 获取已存在的 paper_ids
            existing_states = db.table('user_paper_states').select('paper_id').eq('user_id', USER_ID).execute()
            existing_ids = [row['paper_id'] for row in existing_states.data] if existing_states.data else []
            print(f"已处理的论文数: {len(existing_ids)}")

            # 显示未处理的论文
            if papers_result.data:
                print("\n未处理的论文:")
                count = 0
                for paper in papers_result.data:
                    if paper['id'] not in existing_ids:
                        print(f"  - {paper['id'][:20]}... : {paper['title'][:50]}...")
                        count += 1
                        if count >= 5:
                            break

                if count == 0:
                    print("  (所有论文都已处理)")

if __name__ == "__main__":
    debug_database()
