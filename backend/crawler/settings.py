BOT_NAME = "arxiv_scout"

SPIDER_MODULES = ["crawler.spiders"]
NEWSPIDER_MODULE = "crawler.spiders"

ROBOTSTXT_OBEY = True

# 配置数据管道
ITEM_PIPELINES = {
   # "crawler.pipelines.ArxivApiPipeline": 100, # [DISABLED] Stage 1 不调用 API
   "crawler.pipelines.SupabasePipeline": 300,
}

# 礼貌爬取
DOWNLOAD_DELAY = 3

# 日志级别 (INFO: 只显示重要信息, DEBUG: 显示所有调试信息)
LOG_LEVEL = 'INFO'
