# manual_trigger.py
# 手动触发每日更新工作流 (支持 CLI 参数)
# 用法:
#   python manual_trigger.py                  # 执行完整工作流
#   python manual_trigger.py --resume <ID>    # 恢复工作流

import os
import sys
import argparse
from dotenv import load_dotenv

# 1. 加载环境变量
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(env_path)

# 2. 添加路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.services.scheduler import scheduler_service
from app.services.workflow_engine import WorkflowEngine

def main():
    parser = argparse.ArgumentParser(description="手动触发 ArxivScout 工作流")
    parser.add_argument("--resume", type=str, help="从指定 Execution ID 恢复")
    parser.add_argument("--force", action="store_true", help="强制执行工作流（忽略更新检查，用于断点续传）")
    args = parser.parse_args()
    
    if args.resume:
        print(f"🔄 尝试恢复工作流: {args.resume}")
        engine = WorkflowEngine()
        try:
            engine.resume_workflow(args.resume)
            print(f"✅ 工作流 {args.resume} 恢复并执行完成。")
        except Exception as e:
            print(f"❌ 恢复失败: {e}")
        return

    # 默认：执行完整工作流
    print(f"🚀 启动完整每日工作流 (Force={args.force})...")
    scheduler_service.run_daily_workflow(force=args.force)

if __name__ == "__main__":
    main()
