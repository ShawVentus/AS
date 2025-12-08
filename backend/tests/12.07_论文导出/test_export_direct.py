"""
直接调用 Service 层测试论文导出功能
绕过 API 认证限制
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.services.paper_service import paper_service
from app.schemas.paper import PaperExportRequest

# 测试参数
test_user_id = "你的用户ID"  # 替换为实际的用户ID

# 创建导出请求
export_request = PaperExportRequest(
    user_id='03985519-8f62-48bb-a3ff-f9bae5481a0f',
    date_start="2025-12-07",
    date_end="2025-12-07",
    limit=15,
    format="markdown"  # 或 "json"
)

print("开始导出论文...")
print(f"用户ID: {export_request.user_id}")
print(f"日期范围: {export_request.date_start} 至 {export_request.date_end}")
print(f"数量限制: {export_request.limit}")
print(f"输出格式: {export_request.format}")
print("-" * 50)

# 调用导出功能
result = paper_service.export_papers(export_request)

# 输出结果
if export_request.format == "markdown":
    print("\n=== Markdown 输出 ===\n")
    print(result)
else:
    print("\n=== JSON 输出 ===\n")
    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))

# 保存到文件
output_dir = os.path.join(os.path.dirname(__file__), "result")
os.makedirs(output_dir, exist_ok=True)

if export_request.format == "markdown":
    output_file = os.path.join(output_dir, f"export_{export_request.date_start}.md")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"\n已保存到: {output_file}")
else:
    output_file = os.path.join(output_dir, f"export_{export_request.date_start}.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n已保存到: {output_file}")
