import scrapy

class PaperItem(scrapy.Item):
    id = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    published_date = scrapy.Field()
    category = scrapy.Field()
    abstract = scrapy.Field() # [NEW] 摘要
    # tldr = scrapy.Field() # [REMOVED]
    # details = scrapy.Field() # [REMOVED]
    links = scrapy.Field() # pdf、arxiv、html链接
    comment = scrapy.Field() # 论文备注/评论
    # citation_count = scrapy.Field() # 不需要初始化
