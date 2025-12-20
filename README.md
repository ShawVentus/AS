# ArxivScout Agent 部署迁移指南

一个智能化的 ArXiv 论文推荐与研报生成系统，支持个性化筛选和邮件推送。

---

## 快速迁移清单

```bash
# 1. 创建 Python 环境
conda create -n arxivscout python=3.11 -y
conda activate arxivscout

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 配置环境变量（复制并编辑 .env 文件）
cp .env.example .env  # 然后编辑填入实际配置

# 4. 安装前端依赖
cd ../frontend
npm install

# 5. 启动服务（二选一）
python ../app.py           # 方式1：一键启动前后端
# 或分别启动：
cd ../backend && uvicorn app.main:app --reload --port 8000 &
cd ../frontend && npm run dev
```

---

## 详细部署步骤

### 环境要求

| 组件    | 版本要求 | 安装方式                                               |
| ------- | -------- | ------------------------------------------------------ |
| Python  | 3.11+    | `conda create -n arxivscout python=3.11`               |
| Node.js | 18+      | [官网下载](https://nodejs.org/) 或 `brew install node` |
| npm     | 9+       | 随 Node.js 自动安装                                    |

> **Node.js 安装提示** (macOS)：
>
> ```bash
> # 方式1：使用 Homebrew
> brew install node
>
> # 方式2：使用 nvm（推荐，支持多版本管理）
> curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
> nvm install 18
> nvm use 18
> ```

### 后端配置

`backend/.env` 必需配置项：

```env
# Supabase 数据库
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# LLM 配置（三选一）
LLM_PROVIDER=bohrium  # openrouter / dashscope / bohrium
BOHRIUM_API_KEY=your_api_key

# 邮件配置
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SENDER_EMAIL=your_email@qq.com
SENDER_PASSWORD=your_email_auth_code

# 定时任务
DAILY_REPORT_TIME=09:30
```

### 前端配置

`frontend/.env` 必需配置项：

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

---

## 数据库初始化

首次部署需在 Supabase SQL Editor 中执行 `backend/schema.sql`。

---

## 依赖清单

### Python 依赖 (backend/requirements.txt)

| 包名             | 用途            |
| ---------------- | --------------- |
| fastapi          | Web 框架        |
| uvicorn          | ASGI 服务器     |
| pydantic         | 数据验证        |
| python-dotenv    | 环境变量        |
| supabase         | 数据库客户端    |
| openai           | LLM API         |
| apscheduler      | 定时任务        |
| jinja2           | 邮件模板        |
| scrapy           | ArXiv 爬虫      |
| arxiv            | ArXiv API       |
| bohrium-open-sdk | 玻尔平台 SDK    |
| httpx            | HTTP 客户端     |
| psycopg2-binary  | PostgreSQL 驱动 |
| premailer        | 邮件 CSS 内联   |
| cssutils         | CSS 处理        |

### 前端依赖

自动通过 `npm install` 安装，详见 `frontend/package.json`。

---

## 服务访问地址

| 服务     | 地址                       |
| -------- | -------------------------- |
| 前端     | http://localhost:5173      |
| 后端 API | http://localhost:8000      |
| API 文档 | http://localhost:8000/docs |

---

## 验证部署

```bash
# 验证 Python 依赖
python -c "import fastapi, scrapy, psycopg2, premailer, cssutils; print('✓ 依赖安装成功')"

# 验证后端启动
curl http://localhost:8000/
```

---

## 目录结构

```
AS/
├── app.py                # 一键启动脚本
├── backend/
│   ├── app/              # FastAPI 应用
│   │   ├── api/          # API 路由
│   │   ├── services/     # 业务逻辑
│   │   └── utils/        # 工具函数
│   ├── crawler/          # Scrapy 爬虫
│   ├── requirements.txt  # Python 依赖
│   └── .env              # 环境配置
├── frontend/
│   ├── src/              # React 源码
│   ├── package.json      # Node 依赖
│   └── .env              # 前端配置
└── logs/                 # 运行日志
```

---

## 技术栈

- **后端**: FastAPI + Python 3.11
- **前端**: React + Vite + TailwindCSS
- **数据库**: PostgreSQL (Supabase)
- **LLM**: Qwen (OpenRouter/DashScope/Bohrium)
- **爬虫**: Scrapy

## 许可证

Apache-2.0 License
