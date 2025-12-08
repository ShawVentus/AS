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

load_dotenv()

class ArxivSpider(scrapy.Spider):
    name = "arxiv"
    allowed_domains = ["arxiv.org"]
    
    custom_settings = {
        "LOG_LEVEL": "INFO",
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
        
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]
        
        # 统计数据
        self.stats = {
            "total_found": 0,
            "yielded": 0,
            "skipped_category": 0,
            "categories_found": set()
        }

    def parse(self, response):
        self.logger.info(f"正在解析页面: {response.url}")
        
        # 获取当前页面的分类
        current_category = response.url.split("/list/")[-1].split("/")[0]
        self.stats["categories_found"].add(current_category)
        
        # 提取锚点
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))
        
        self.logger.debug(f"找到 {len(anchors)} 个锚点")
        
        dt_elements = response.xpath('//dl[@id="articles"]/dt')
        dd_elements = response.xpath('//dl[@id="articles"]/dd')
        
        items_to_yield = []

        for dt, dd in zip(dt_elements, dd_elements):
            self.stats["total_found"] += 1
            
            # 提取ArXiv ID
            paper_anchor = dt.xpath('./a[@name]/@name').get()
            if paper_anchor and "item" in paper_anchor:
                paper_id_num = int(paper_anchor.split("item")[-1])
                if anchors and paper_id_num >= anchors[-1]:
                    continue

            arxiv_id_text = dt.xpath('.//a[@title="Abstract"]/text()').get()
            if not arxiv_id_text:
                continue
            
            arxiv_id = arxiv_id_text.replace("arXiv:", "").strip()
            self.logger.debug(f"发现论文: {arxiv_id}")
            
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

            # [UPDATED] 过滤：只要任意一个分类在目标类别中就保留
            # 检查 all_tags 和 target_categories 是否有交集
            if not any(tag in self.target_categories for tag in all_tags):
                self.logger.debug(f"跳过 {arxiv_id} - 分类不匹配 {all_tags}")
                self.stats["skipped_category"] += 1
                continue

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
        else:
            self.logger.info(f"No papers found for {current_category} matching criteria.")

    def closed(self, reason):
        """爬虫关闭时输出总结"""
        print("\n" + "="*50)
        print("🔍 ArXiv 爬虫执行总结")
        print("="*50)
        print(f"📅 目标分类: {', '.join(self.target_categories)}")
        print(f"📂 实际扫描分类: {', '.join(self.stats['categories_found'])}")
        print(f"📄 总共发现论文: {self.stats['total_found']}")
        print(f"✅ 捕获并提交处理: {self.stats['yielded']}")
        print(f"🚫 因分类不符跳过: {self.stats['skipped_category']}")
        
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
