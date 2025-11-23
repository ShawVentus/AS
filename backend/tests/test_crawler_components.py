import sys
import os
from pathlib import Path
import requests
import json
from datetime import datetime
from scrapy.http import HtmlResponse, Request
from dotenv import load_dotenv

# ==========================================
# 🔧 测试配置 (Configuration)
# ==========================================
TARGET_CATEGORY = "cs.CL"       # 目标测试类别
TEST_BATCH_SIZE = 100             # 阶段 2 测试的论文数量
REQUEST_TIMEOUT = 10            # 网页请求超时时间 (秒)
# ==========================================

# 添加 backend 目录到 Python 路径，确保能导入 crawler 模块
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# 导入我们的爬虫组件
from crawler.spiders.arxiv import ArxivSpider
from crawler.pipelines import ArxivApiPipeline
from crawler.items import PaperItem

# 加载环境变量
load_dotenv(backend_dir / ".env")

# 结果存储目录
OUTPUT_DIR = backend_dir / "tests" / "crawler"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_json(data, filename):
    """保存数据到 JSON 文件"""
    filepath = OUTPUT_DIR / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"💾 结果已保存至: {filepath}")

def test_spider_extraction():
    """
    测试阶段 1: 验证 Spider 能否从网页正确提取 ID 和分类
    """
    print("\n" + "="*50)
    print("🧪 测试阶段 1: 爬虫网页解析 (获取 ID 和分类)")
    print("="*50)

    # 1. 模拟请求 arXiv 列表页
    url = f"https://arxiv.org/list/{TARGET_CATEGORY}/new"
    print(f"📡 正在请求网页: {url} ...")
    
    try:
        # 使用 requests 获取真实网页内容
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.content
        print("✅ 网页获取成功")
    except Exception as e:
        print(f"❌ 网页获取失败: {e}")
        return []

    # 2. 构建 Scrapy Response 对象 (模拟 Scrapy 的响应)
    scrapy_response = HtmlResponse(
        url=url,
        body=html_content,
        encoding='utf-8',
        request=Request(url=url)
    )

    # 3. 实例化 Spider 并调用 parse 方法
    spider = ArxivSpider()
    print("🕷️  正在运行 Spider.parse() ...")
    
    extracted_items = []
    # parse 方法返回的是一个生成器，我们需要遍历它
    for item in spider.parse(scrapy_response):
        if isinstance(item, PaperItem):
            # 将 Item 转换为字典以便序列化
            extracted_items.append(dict(item))
    
    # 4. 验证结果并保存
    print(f"📊 提取结果: 找到 {len(extracted_items)} 篇论文")
    
    # 保存阶段 1 结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_json(extracted_items, f"stage1_spider_ids_{timestamp}.json")
    
    if len(extracted_items) > 0:
        first_item = extracted_items[0]
        print(f"\n📝 示例数据 (第一篇):")
        print(f"   - ID: {first_item.get('id')}")
        print(f"   - Category: {first_item.get('category')}")
        print("✅ 阶段 1 测试通过！")
        return extracted_items
    else:
        print("❌ 阶段 1 测试失败: 未提取到任何论文")
        return []

def test_api_enrichment(raw_items):
    """
    测试阶段 2: 验证 Pipeline 能否通过 API 补全论文信息
    """
    print("\n" + "="*50)
    print(f"🧪 测试阶段 2: API 元数据获取 (测试前 {min(len(raw_items), TEST_BATCH_SIZE)} 篇)")
    print("="*50)
    
    if not raw_items:
        print("⚠️  跳过阶段 2: 因为阶段 1 未返回有效数据")
        return

    # 1. 实例化 Pipeline
    pipeline = ArxivApiPipeline()
    print("🔧 Pipeline 初始化完成")

    # 模拟 Spider 对象 (Pipeline 需要用到 spider.logger)
    class MockSpider:
        class Logger:
            def info(self, msg): print(f"   [INFO] {msg}")
            def warning(self, msg): print(f"   [WARN] {msg}")
            def error(self, msg): print(f"   [ERROR] {msg}")
        logger = Logger()
    
    mock_spider = MockSpider()

    enriched_results = []
    
    # 2. 批量处理
    items_to_process = raw_items[:TEST_BATCH_SIZE]
    
    for i, raw_item in enumerate(items_to_process, 1):
        print(f"\n[{i}/{len(items_to_process)}] 🔄 正在处理论文 ID: {raw_item['id']} ...")
        
        try:
            # process_item 会修改传入的 item，所以我们传入一个副本
            item_to_process = raw_item.copy()
            enriched_item = pipeline.process_item(item_to_process, mock_spider)
            enriched_results.append(dict(enriched_item))
            
            # 简单验证
            if enriched_item.get('title'):
                print(f"   ✅ 获取成功: {enriched_item.get('title')[:50]}...")
            else:
                print("   ❌ 获取失败: 标题为空")
                
        except Exception as e:
            print(f"   ❌ 处理出错: {e}")

    # 3. 保存结果
    if enriched_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_json(enriched_results, f"stage2_api_details_{timestamp}.json")
        print("\n✅ 阶段 2 测试完成！")
    else:
        print("\n❌ 阶段 2 测试失败: 未获取到任何结果")

if __name__ == "__main__":
    print("🚀 开始运行爬虫组件测试...")
    print(f"📂 结果将保存至: {OUTPUT_DIR}")
    print(f"⚙️  配置: Category={TARGET_CATEGORY}, BatchSize={TEST_BATCH_SIZE}")
    
    # 运行阶段 1
    items = test_spider_extraction()
    
    # 运行阶段 2
    if items:
        test_api_enrichment(items)
    else:
        # 如果阶段 1 失败，使用硬编码数据测试
        print("\n⚠️  尝试使用硬编码 ID 进行阶段 2 测试...")
        dummy_items = [{
            'id': "1706.03762",
            'category': ["cs.CL"],
            'title': "",
            'authors': [],
            'published_date': "",
            'tldr': "",
            'details': {},
            'links': {},
            'comment': ""
        }]
        test_api_enrichment(dummy_items)
