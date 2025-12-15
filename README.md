### 2025-12-15 17:49:29
TODO: 初始化引导 + debug + 引导文字
1. 用户初始化过程优化
2. api 优化 ，为什么会重复调用那么多次，逻辑debug（不重要，可以后面慢慢优化
3. 测试多用户报告生成功能
4. 首页显示：已为您生成个性化论文/报告 XX 篇，今天是为您服务的第 xx 天
5. 增加错误发送邮箱
6. api 改为 玻尔官方的，根据限流情况更改 api 调用速率
7. 注册与用户管理向玻尔适配
8. 邮件页面优化，显示尾作
9. 修改分析 prompt，避免同质化的语言
10. 是否删除历史研报中生成研报功能

### 2025-12-15 10:36:38 - 2025-12-15 17:49:32
1. 将进度和用户填写的信息放到额外的单独页面一起显示，现在是弹窗，且关闭后就没了，固定在单一页面内 - 2025-12-15 12:34:44
2. 增加用户笔记功能
3. 第一次使用的用户在周末生成报告的话，显示的不应该是当日的日期，而是论文实际挂在arxiv上的日期
4. 增加论文页面回到顶部按钮，保持顶栏不移动
5. 发现 arxiv 数量对不上的问题 - 逻辑没问题，显示上的问题，爬虫获取需要写入的论文数并未去重，而真正在数据库中的论文是去重过的
6. 修复数据重载、任务进度丢失、全局通知的问题，预加载论文和报告页面的数据，并存入缓存
7. 优化报告显示页面，修复缩进和句号多余空格问题，更换摘要ui
8. 优化预览/详情卡片显示
9. 论文页面能显示：显示论文/所有论文：35/120
10. 修复头像显示 bug
11. 增加报告和论文详情页动态效果与模糊效果

### 2025-12-14 14:14:55
已经实现前后端状态的实时交互

### 2025-12-12 15:38:17 - 2025-12-12 22:33:52
1. 前后端交互优化，实时显示报告生成进度 - 尝试通过数据库转发状态，但是前端没有办法接收后端的状态
2. 修改 arxiv 逻辑，如果重复就不访问对应的页面爬取论文
3. 论文管理的筛选功能，支持类别多选，并且显示的类别是根据相关度筛选后的结果

### 2025-12-11 23:00:18 - 2025-12-12 15:37:55
测试前后端其他功能，确保没有显示 bug
  - 报告生成 + 个性化生成 提示词 debug
    - 实现 _parse_report_response(response_text) 辅助函数。
    - 使用正则表达式 (re) 提取 <title>, <summary>, <content> 标签内的内容。
    - 优化 filter 提示词
  - 报告生成 增加 deepseek 回退
    - 增加报警功能
    - 修正计数错误
优化日期显示：前端显示的日期是论文创建日期，创建时全部填入为当日的字段
计算成本
修改定时时间为 9:30，冬令时北京时间早上九点更新，预留半小时防止服务器过载

### 2025-12-12 17:48:26 - 2025-12-11 22:59:28
支持成本控制，完善日志记录与输出，优化pipeline
debug 前后端的部分功能
明确调用成本

### 2025-12-11 10:53:20
完善 html 模板，实现邮件发送功能

### 2025-12-09 22:24:54
完善邮件发送功能，形成pipeline，待测试功能完整性，待增加用户引导语平台适配设置

### 2025-12-08 20:56:48
优化论文显示页面，优化交互体验

### 2025-12-08 10:33:29
完善 report prompt
预填入报告，准备前端渲染实现
实现个性化论文生成pipeline

### 2025-12-06 20:33:27
实现前端论文显示界面

### 2025-12-05 22:37:15
scheduler 中实现分析论文与更新用户私有数据库论文的功能
新建 daily_papers 表，用于存放每日更新的论文

### 2025-12-04 15:39:50
实现输入用户 id 即可更新用户私有数据库论文：paper_service.get_papers_by_categories

### 2025-11-29 20:28:44
完全移除模拟数据
完善初始化流程与用户画像初始化
完善 TODO

### 2025-11-29 14:34:38
完善公共论文分析功能，根据 status 判断论文状态，将 completed 状态的论文分析后更新到数据库中设置状态为 analyzed

### 2025-11-29 13:25:50
优化前端体验
初步完善用户初始化界面 w
优化论文获取逻辑，增加 calendar 功能
优化个人信息设置界面，增加头像上传功能
增加加载的等待界面，首次进入应用时显示 LoadingScreen

### 2025-11-28 17:38:25
添加邮箱注册与登录功能，后续将会实现私有数据库管理

- **用户管理**：注册后没有对应的个人信息，注册时应当搜集用户名等信息。注册后，前端右上角会显示对应的初始头像，点击头像可以进入设置界面。而初始化头像为用户用户名首字母大写/中文，像谷歌一样给到随机颜色的背景。此外，初始化时需要让用户自行初始化需求（将用于生成每日论文推荐，您后续可以随时更改您的需求）
- **个性化用户画像管理**：作者机构支持手动添加，支持改名字头像。支持通过自然语言更新画像（调用简单的免费小型 LLM），更新最近的需求
- **LLM 更新**：调用 LLM 会更新公共论文数据库中的 details 和特定用户私有数据库中的论文，并维护更新对应的字段
- **前端论文显示与管理**：在用户的私有论文库构建完成后，检验前端显示情况，能否显示当日论文与过去论文（时间以在私有数据库中创建为准），并且能够实现链接访问等功能。批量下载后面再说。需要实现 like 字段的存储（like 的意思是以后多生成对应的论文）
- **自动化研报**：
- **自动化邮件**：

### 2025-11-28 15:25:39

优化论文获取与存储到数据库的功能

```bash
# 一次性完成两个阶段
conda activate arxivscout
cd backend

# Stage 1: 抓取 ID 和分类 (约 20-30 秒)
scrapy crawl arxiv

# Stage 2: 获取详细信息 (根据论文数量，可能需要几分钟)
python -m crawler.fetch_details
```

### 2025-11-23 15:45:50

调整代码结构，删除冗余部分

### 2025-11-23 11:03:43

完善前端和爬虫，准备逐步完善其他功能

# Paper Scout Agent (论文侦察兵)

Paper Scout Agent 是一个智能化的论文查询与阅读助手，旨在通过个性化记忆模块，为您提供精准的论文筛选、深度分析、研报生成及邮件推送服务。

## 核心特性

- **个性化记忆**: 基于您的阅读历史和反馈（Like/Dislike），不断进化推荐算法。
- **智能分析**: 利用 Qwen LLM 深度解读论文，提取 TLDR、创新点和关键结论。
- **自动化研报**: 每日自动聚合最新论文，生成综述型研报并发送邮件。
- **交互式前端**: 现代化的 React 界面，支持深色模式、交互式引用和可视化记忆仪表盘。

## 技术栈

- **Frontend**: React, Vite, TailwindCSS, Lucide Icons
- **Backend**: FastAPI, Python 3.11
- **Database**: PostgreSQL (via Supabase)
- **LLM**: Qwen (DashScope API)
- **Crawler**: Scrapy
- **Deployment**: Docker Compose

## 快速开始 (Docker 部署)

### 1. 前置准备

- 安装 [Docker](https://www.docker.com/) 和 [Docker Compose](https://docs.docker.com/compose/install/)。
- 注册 [Supabase](https://supabase.com/) 账号并创建一个新项目。
- 获取 [DashScope (通义千问)](https://dashscope.aliyun.com/) API Key。
- 准备一个支持 SMTP 的邮箱（如 QQ 邮箱）用于发送研报。

### 2. 数据库初始化

1. 登录 Supabase Dashboard，进入项目的 **SQL Editor**。
2. 复制本项目 `backend/schema.sql` 文件的全部内容。
3. 在 SQL Editor 中执行该脚本，创建必要的数据表和安全策略。

### 3. 环境变量配置

在项目根目录下创建或修改 `.env` 文件（参考 `backend/.env` 和 `frontend/.env`）：

**Backend (`backend/.env`)**:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
DASHSCOPE_API_KEY=your_dashscope_api_key
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SENDER_EMAIL=your_email@qq.com
SENDER_PASSWORD=your_email_password
```

**Frontend (`frontend/.env`)**:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_PORT=5173
```

### 4. 启动服务

在项目根目录下运行：

```bash
docker-compose up --build
```

启动成功后：

- **前端访问**: [http://localhost:5173](http://localhost:5173)
- **后端 API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 手动开发运行

### 后端

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 目录结构

- `backend/`: FastAPI 服务、爬虫、LLM 逻辑
  - `api/`: API 路由
  - `models/`: Pydantic 数据模型
  - `services/`: 核心业务逻辑 (Paper, User, Report)
  - `spiders/`: Scrapy 爬虫
  - `prompt/`: LLM 提示词模板
- `frontend/`: React 应用
  - `src/components/`: UI 组件
  - `src/services/`: API 客户端
  - `src/types/`: TypeScript 类型定义

## 许可证

MIT License
