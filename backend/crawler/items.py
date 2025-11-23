import scrapy

class PaperItem(scrapy.Item):
    id = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    published_date = scrapy.Field()
    category = scrapy.Field()
    tldr = scrapy.Field()
    # tags = scrapy.Field() # 已合并到 category
    details = scrapy.Field() # 摘要、动机等
    links = scrapy.Field() # pdf、arxiv、html链接
    comment = scrapy.Field() # 论文备注/评论
    # citation_count = scrapy.Field() # 不需要初始化
