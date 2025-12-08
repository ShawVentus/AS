# manual_trigger.py
# 手动触发每日更新工作流 (强制执行，忽略日期检查)
# 用于验证：爬虫 -> Daily DB -> Analysis -> Public DB 的完整链路

# 1. 优先加载环境变量 (指定 backend/.env 路径)
# 必须在导入 app.core.config 之前加载，否则 config 中的 os.getenv 取不到值
import os
from dotenv import load_dotenv
import sys

env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(env_path)

# 将 backend 添加到系统路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.services.scheduler import SchedulerService
from app.services.paper_service import PaperService
from app.services.workflow_service import workflow_service


import time

def manual_run():
    start_time = time.time()
    print("🚀 正在启动手动触发器...")
    
    scheduler = SchedulerService()
    paper_service = PaperService()
    
    # 1. 检查更新并获取分类
    print("\n🔍 第 1 步：正在检查 Arxiv 更新...")
    categories = scheduler.check_arxiv_update()
    
    if not categories:
        print("⚠️  未检测到 Arxiv 更新。手动触发停止。")
        return
        
    print(f"✅ 检测到更新！待爬取的分类：{categories}")
    
    # 2. 强制清空每日数据库 (可选，但建议在手动触发时执行以确保环境干净)
    print("\n🗑️  第 2 步：正在清空每日论文数据...")
    if paper_service.clear_daily_papers():
        print("✅ 每日论文已清空。")
    else:
        print("❌ 清空每日论文失败。")
        return

    # 3. 公共工作流
    print("\n🌍 第 3 步：正在运行公共论文工作流...")
    try:
        workflow_service.process_public_papers_workflow(categories)
    except Exception as e:
        print(f"❌ 公共工作流失败：{e}")
        return

    # 4. 个性化筛选
    print("\n👤 第 4 步：正在运行个性化筛选...")
    try:
        scheduler.process_personalized_papers()
        print("✅ 个性化筛选完成。")
    except Exception as e:
        print(f"❌ 个性化筛选失败：{e}")
        return

    end_time = time.time()
    duration = end_time - start_time
    print(f"\n🎉 手动运行成功完成！总耗时: {duration:.2f} 秒")

if __name__ == "__main__":
    manual_run()