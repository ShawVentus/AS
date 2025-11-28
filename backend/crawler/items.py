import scrapy

class PaperItem(scrapy.Item):
    id = scrapy.Field()
    title = scrapy.Field()
    authors = scrapy.Field()
    published_date = scrapy.Field()
    category = scrapy.Field()
    abstract = scrapy.Field()
    links = scrapy.Field()
    comment = scrapy.Field()
    # details 字段在 Stage 1 不需要填充，留给 Stage 3
    # status 字段在 Pipeline 中处理
