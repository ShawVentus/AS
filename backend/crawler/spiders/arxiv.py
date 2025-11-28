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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = os.getenv("CATEGORIES", "cs.LG,cs.AI")
        self.target_categories = set(map(str.strip, categories.split(",")))
        self.start_urls = [
            f"https://arxiv.org/list/{cat}/new" for cat in self.target_categories
        ]

    def parse(self, response):
        print(f"DEBUG: Parsing {response.url}")
        # 解析新论文列表页面
        # 结构: <dt> (元数据链接) <dd> (标题、作者等)
        
        # 获取当前页面的分类
        # URL格式: https://arxiv.org/list/cs.LG/new
        current_category = response.url.split("/list/")[-1].split("/")[0]
        print(f"DEBUG: Category {current_category}")
        
        # 提取锚点以过滤论文
        anchors = []
        for li in response.css("div[id=dlpage] ul li"):
            href = li.css("a::attr(href)").get()
            if href and "item" in href:
                anchors.append(int(href.split("item")[-1]))
        
        print(f"DEBUG: Found {len(anchors)} anchors")

        dt_elements = response.xpath('//dl[@id="articles"]/dt')
        dd_elements = response.xpath('//dl[@id="articles"]/dd')
        
        for dt, dd in zip(dt_elements, dd_elements):
            # 提取ArXiv ID
            # <a name="item-id-2310.12345"></a>
            paper_anchor = dt.xpath('./a[@name]/@name').get()
            if paper_anchor and "item" in paper_anchor:
                paper_id_num = int(paper_anchor.split("item")[-1])
                if anchors and paper_id_num >= anchors[-1]:
                    continue

            arxiv_id_text = dt.xpath('.//a[@title="Abstract"]/text()').get()
            if not arxiv_id_text:
                continue
            # 清理 ID: 去除 "arXiv:" 和空白字符
            arxiv_id = arxiv_id_text.replace("arXiv:", "").strip()
            print(f"DEBUG: Found paper {arxiv_id}")
            
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
                print(f"DEBUG: Skipping {arxiv_id} - no matching categories in {all_tags}")
                continue

            # 构建基础数据项 (仅包含ID和分类列表)
            # 详细信息将由 Stage 2 通过 API 获取
            item = PaperItem()
            item["id"] = arxiv_id
            item["category"] = all_tags 
            
            # 初始化其他字段为空，避免 Pipeline 报错
            item["title"] = ""
            item["authors"] = []
            item["published_date"] = ""
            item["links"] = {}
            item["comment"] = ""
            
            yield item
