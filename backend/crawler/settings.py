BOT_NAME = "arxiv_scout"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

ROBOTSTXT_OBEY = True

# 配置数据管道
ITEM_PIPELINES = {
   "crawler.pipelines.ArxivApiPipeline": 100,
   "crawler.pipelines.SupabasePipeline": 300,
}

# 礼貌爬取
DOWNLOAD_DELAY = 3
