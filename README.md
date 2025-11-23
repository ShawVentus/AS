# 2025-11-23 11:03:43
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
python -m uvicorn main:app --reload --port 8000
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
