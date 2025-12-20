"""
AS 项目爬虫 - arXiv Spider
功能: 负责从 arXiv 网站抓取最新的论文 ID 和分类信息。
逻辑: 
1. 访问 arXiv 列表页 (如 https://arxiv.org/list/cs.LG/new)。
2. 解析 HTML 提取论文 ID 和分类。
3. 生成 PaperItem 传递给 Pipeline 进行后续处理 (API 获取详情)。
"""
import scrapy
import re
import os
from crawler.items import PaperItem
from dotenv import load_dotenv
from scrapy.exceptions import CloseSpider
from datetime import datetime
import sys

# 确保 backend 根目录在 sys.path 中，以便导入 app 模块
# Ensure backend root is in sys.path to import app modules
current_file = os.path.abspath(__file__)
crawler_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
if crawler_dir not in sys.path:
    sys.path.append(crawler_dir)

from app.utils.email_sender import email_sender
from app.core.database import get_db

load_dotenv()

class ArxivSpider(scrapy.Spider):
    name = "arxiv"
    allowed_domains = ["arxiv.org"]
    
    custom_settings = {
        "LOG_LEVEL": "INFO",
        # [NEW] 重试配置
        "RETRY_ENABLED": True,  # 启用重试中间件
        "RETRY_TIMES": 3,  # 重试次数
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 522, 524, 408, 429],  # 需要重试的HTTP状态码
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🤫 静音 httpx 和 scrapy 的冗余日志，只保留 WARNING 及以上
        import logging
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("scrapy").setLevel(logging.WARNING)
        
        # 优先使用传入的 categories 参数，否则使用环境变量
        # categories 参数可能是逗号分隔的字符串
        if hasattr(self, 'categories') and self.categories:
            categories_str = self.categories
        else:
            categories_str = os.getenv("CATEGORIES")

        if not categories_str:
            self.target_categories = set()
        else:
            self.target_categories = set(map(str.strip, categories_str.split(",")))
        
        # [REMOVED] start_urls - 改用 start_requests() 方法以支持 errback
        # self.start_urls = [
        #     f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        # ]
        
        # 统计数据
        self.stats = {
            "total_found": 0,
            "unique_found": 0, # [NEW] 去重后的数量
            "yielded": 0,
            "skipped_category": 0,
            "categories_found": set(),
            "all_subcategories": set(),  # [NEW] 所有论文的子类别标签（去重）
            "failed_categories": []  # [NEW] 爬取失败的类别列表
        }
        self.seen_ids = set() # [NEW] 用于本次爬取会话去重
        
        # 数据库连接
        self.db = get_db()
        self.date_saved = False # 标志位，避免重复写入日期
    
    def start_requests(self):
        """
        生成初始请求。
        
        为每个目标类别生成请求，并添加 errback 钩子以捕获失败。
        
        Yields:
            scrapy.Request: 带有 callback 和 errback 的请求对象
        """
        for cat in self.target_categories:
            url = f"https://arxiv.org/list/{cat}/new"
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                errback=self.handle_error,  # 捕获所有类型的请求失败
                meta={'category': cat},  # 传递类别信息给 errback
                dont_filter=True  # 允许重试时重复请求同一个 URL
            )

    def parse(self, response):
        self.logger.info(f"正在解析页面: {response.url}")
        
        # 获取当前页面的分类
        current_category = response.url.split("/list/")[-1].split("/")[0]
        self.stats["categories_found"].add(current_category)
        
        # --- [NEW] 严格日期解析 (Strict Date Parsing) ---
        if not self.date_saved:
            try:
                # 尝试提取日期文本
                # 目标格式: "Showing new listings for Monday, 15 December 2025"
                # XPath: //div[@id="dlpage"]/h3
                h3_text = response.xpath('//div[@id="dlpage"]/h3/text()').get()
                
                if not h3_text:
                    raise ValueError("无法找到包含日期的 h3 标签 (h3 tag not found)")
                
                # 使用正则提取日期部分
                # 匹配模式: 星期, 日 月 年 (e.g., Monday, 15 December 2025)
                match = re.search(r'listings for\s+(?:[a-zA-Z]+,\s+)?(\d{1,2}\s+[a-zA-Z]+\s+\d{4})', h3_text)
                
                if not match:
                    raise ValueError(f"日期格式不匹配 (Date format mismatch): {h3_text}")
                
                date_str = match.group(1)
                # 解析为 datetime 对象
                # %d %B %Y -> 15 December 2025
                arxiv_date_obj = datetime.strptime(date_str, "%d %B %Y")
                arxiv_date_iso = arxiv_date_obj.strftime("%Y-%m-%d")
                
                self.logger.info(f"✅ 成功解析 ArXiv 日期: {arxiv_date_iso} (from '{h3_text}')")
                
                # 存入数据库 system_status
                self.db.table("system_status").upsert({
                    "key": "latest_arxiv_date",
                    "value": arxiv_date_iso,
                    "updated_at": datetime.now().isoformat()
                }).execute()
                
                self.date_saved = True
                
            except Exception as e:
                error_msg = f"🛑 严重错误: ArXiv 日期解析失败 (Critical: Failed to parse ArXiv date).\nURL: {response.url}\nError: {str(e)}"
                self.logger.error(error_msg)
                
                # 发送报警邮件
                try:
                    email_sender.send_email(
                        to_email="2962326813@qq.com",
                        subject="【系统报警】ArXiv 爬虫日期解析失败",
                        html_content=f"<p>{error_msg}</p>",
                        plain_content=error_msg
                    )
                except Exception as email_e:
                    self.logger.error(f"发送报警邮件失败: {email_e}")
                
                # 严格模式：停止爬虫
                raise CloseSpider(f"Date parsing failed: {str(e)}")
        # ------------------------------------------------
        
        # 提取 "Replacements" 的锚点
        replacement_anchor = None
        for li in response.css("div[id=dlpage] ul li"):
            a_text = li.css("a::text").get()
            href = li.css("a::attr(href)").get()
            # Check for "Replacements" or "Replacement submissions"
            if a_text and "Replacement" in a_text and href and "item" in href:
                try:
                    replacement_anchor = int(href.split("item")[-1])
                    self.logger.info(f"Found Replacements anchor: {replacement_anchor}")
                    break
                except ValueError:
                    pass
        
        dt_elements = response.xpath('//dl[@id="articles"]/dt')
        dd_elements = response.xpath('//dl[@id="articles"]/dd')
        
        items_to_yield = []

        for dt, dd in zip(dt_elements, dd_elements):
            self.stats["total_found"] += 1
            
            # 提取ArXiv ID
            paper_anchor = dt.xpath('./a[@name]/@name').get()
            if paper_anchor and "item" in paper_anchor:
                try:
                    paper_id_num = int(paper_anchor.split("item")[-1])
                    # 只有当找到了 replacement_anchor 且当前 ID 大于等于它时才跳过
                    if replacement_anchor is not None and paper_id_num >= replacement_anchor:
                        self.logger.debug(f"Skipping replacement paper at anchor {paper_id_num}")
                        continue
                except ValueError:
                    pass

            arxiv_id_text = dt.xpath('.//a[@title="Abstract"]/text()').get()
            if not arxiv_id_text:
                continue
            
            arxiv_id = arxiv_id_text.replace("arXiv:", "").strip()
            self.logger.debug(f"发现论文: {arxiv_id}")
            
            # [NEW] 统计去重数量
            if arxiv_id not in self.seen_ids:
                self.seen_ids.add(arxiv_id)
                self.stats["unique_found"] += 1
            
            # 提取所有分类 (Tags)
            # 结构: <div class="list-subjects">
            # <span class="primary-subject">Primary (cs.XX)</span>; Secondary (cs.YY)
            # </div>
            subjects_div = dd.xpath('.//div[contains(@class, "list-subjects")]')
            
            # 提取主类别 (Primary Subject)
            primary_subject_text = subjects_div.xpath('.//span[@class="primary-subject"]/text()').get()
            primary_category = None
            
            if primary_subject_text:
                # 从 "Computer Vision and Pattern Recognition (cs.CV)" 提取 "cs.CV"
                match = re.search(r'\(([^\)]+)\)', primary_subject_text)
                if match:
                    primary_category = match.group(1)
            
            # 提取所有分类标签（包括主类别和次类别）
            subjects_text = subjects_div.get()
            all_tags = []
            if subjects_text:
                # 提取所有括号内的分类代码，如 (cs.CV), (math.OT), (eess.IV)
                found_tags = re.findall(r'\(([\w\.-]+)\)', subjects_text)
                # 使用 dict.fromkeys 保留顺序去重
                all_tags = list(dict.fromkeys(found_tags))
            
            # 确保主类别在 tags 列表的第一位
            if primary_category and primary_category not in all_tags:
                all_tags.insert(0, primary_category)
            elif primary_category and primary_category in all_tags:
                # 将主类别移到第一位
                all_tags.remove(primary_category)
                all_tags.insert(0, primary_category)

            # [DISABLED] 分类过滤已禁用 - 获取所有论文（Replacements除外）
            # 原逻辑：只保留分类标签与 target_categories 有交集的论文
            # if not any(tag in self.target_categories for tag in all_tags):
            #     self.logger.debug(f"跳过 {arxiv_id} - 分类不匹配 {all_tags}")
            #     self.stats["skipped_category"] += 1
            #     continue

            # 构建 Item
            item = PaperItem()
            item["id"] = arxiv_id
            item["category"] = all_tags 
            item["title"] = ""
            item["authors"] = []
            item["published_date"] = ""
            item["links"] = {}
            item["comment"] = ""
            
            items_to_yield.append(item)
            
            # [NEW] 收集该论文的所有子类别标签
            for tag in all_tags:
                self.stats["all_subcategories"].add(tag)
            
        # 开始写入数据库 (可视化进度)
        from tqdm import tqdm
        import sys
        
        if items_to_yield:
            pbar = tqdm(
                total=len(items_to_yield), 
                desc=f"Saving {current_category} to DB", 
                unit="paper",
                file=sys.stdout,
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
            
            for item in items_to_yield:
                self.stats["yielded"] += 1
                yield item
                pbar.update(1)
                
            pbar.close()
            
            # [NEW] 实时显示该页面的爬取进度
            print(f"✅ {current_category}: 抓取到 {len(items_to_yield)} 篇论文")
        else:
            # [MODIFIED] 显示未找到论文的提示
            print(f"⚠️  {current_category}: 未找到符合条件的论文")
    
    def handle_error(self, failure):
        """
        处理请求失败。
        
        当请求因网络错误、HTTP错误或其他原因失败时，此方法会被调用。
        记录失败信息并打印友好提示，避免整个爬取流程中断。
        
        Args:
            failure: Scrapy 的 Failure 对象，包含错误信息
        """
        # 从 meta 中获取类别信息
        category = failure.request.meta.get('category', 'unknown')
        
        # 获取错误详情
        error_msg = str(failure.value)
        
        # 记录失败的类别
        self.stats["failed_categories"].append({
            "category": category,
            "error": error_msg
        })
        
        # 打印友好提示
        print(f"❌ {category}: 爬取失败 - {error_msg}")
        self.logger.error(f"Failed to crawl {category}: {failure}")

    def closed(self, reason):
        """爬虫关闭时输出总结"""
        print("\n" + "="*50)
        print("🔍 ArXiv 爬虫执行总结")
        print("="*50)
        print(f"📅 目标分类: {', '.join(self.target_categories)}")
        print(f"📂 实际扫描分类: {', '.join(self.stats['categories_found'])}")
        print(f"📄 总共发现论文 (去重后): {self.stats['unique_found']} (原始抓取: {self.stats['total_found']})")
        print(f"✅ 捕获并提交处理: {self.stats['yielded']}")
        print(f"🚫 因分类不符跳过: {self.stats['skipped_category']}")
        
        # [NEW] 显示失败的类别
        if self.stats['failed_categories']:
            print(f"❌ 爬取失败的类别: {len(self.stats['failed_categories'])} 个")
            for failed in self.stats['failed_categories']:
                print(f"   - {failed['category']}: {failed['error']}")
        
        # 尝试获取 Pipeline 的统计信息 (如果 Pipeline 更新了 crawler.stats)
        inserted = self.crawler.stats.get_value('papers/inserted', 0)
        duplicates = self.crawler.stats.get_value('papers/duplicates', 0)
        failed = self.crawler.stats.get_value('papers/failed', 0)
        
        if inserted or duplicates or failed:
            print("-" * 30)
            print("💾 数据库处理结果:")
            print(f"   🆕 新增入库: {inserted}")
            print(f"   ♻️ 重复/已存在: {duplicates}")
            print(f"   ❌ 处理失败: {failed}")
        
        print("="*50 + "\n")
        
        # [NEW] 输出机器可读的统计信息，供 WorkflowStep 解析
        # 必须确保 unique_found 是去重后的数量
        import json
        # Convert sets to list for JSON serialization if any
        stats_serializable = self.stats.copy()
        if "categories_found" in stats_serializable:
            stats_serializable["categories_found"] = list(stats_serializable["categories_found"])
        # [NEW] 转换 all_subcategories 为列表
        if "all_subcategories" in stats_serializable:
            stats_serializable["all_subcategories"] = list(stats_serializable["all_subcategories"])
            
        print(f"JSON_STATS:{json.dumps(stats_serializable)}")
