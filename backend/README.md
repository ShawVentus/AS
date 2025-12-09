# 后端功能与测试指南 (Backend README)

本文档旨在帮助开发者快速了解后端核心功能，并提供详细的操作指南来测试从论文获取、过滤到报告生成的完整 Pipeline。

## 📂 核心功能文件概览

| 文件路径 | 主要类/模块 | 功能描述 |
| :--- | :--- | :--- |
| `app/services/workflow_service.py` | `WorkflowService` | **公共工作流入口**。负责协调爬虫、Arxiv API 数据补全、公共分析 (TLDR/Motivation) 以及数据归档。 |
| `app/services/scheduler.py` | `SchedulerService` | **定时任务与个性化流程**。负责每日定时触发、个性化论文筛选 (`process_personalized_papers`) 以及报告生成与发送 (`generate_report_job`)。 |
| `app/services/paper_service.py` | `PaperService` | **论文核心服务**。提供论文的增删改查、LLM 批量过滤 (`filter_papers`)、批量分析等底层逻辑。 |
| `app/services/report_service.py` | `ReportService` | **报告与邮件服务**。负责生成 Markdown/HTML 报告，并调用邮件系统发送给用户。 |
| `app/api/v1/endpoints/workflow.py` | `router` | **工作流 API**。提供手动触发后端任务的 HTTP 接口。 |

---

## 🧪 测试指南

你可以通过 **命令行 (CLI)** 或 **API 接口** 两种方式来测试 Pipeline。

### 前置条件
1. 确保已激活 Conda 环境: `conda activate arxivscout` (或你的环境名)
2. 确保 `.env` 文件已配置正确 (数据库、LLM Key、邮件配置等)。
3. 确保后端目录为当前工作目录: `cd backend`

### 方式一：命令行测试 (推荐开发调试)

这种方式可以直接调用 Service 函数，适合调试具体环节，能直接在终端看到打印日志。

#### 1. 测试完整每日工作流 (All-in-One)
这将执行：检查更新 -> 爬虫 -> 公共分析 -> 个性化筛选 -> 生成报告 -> 发送邮件。
```bash
python -c "from app.services.scheduler import scheduler_service; scheduler_service.run_daily_workflow()"
```

#### 2. 仅测试“爬虫 + 公共分析” (Public Workflow)
如果你只想抓取新论文并存入数据库，不进行个性化筛选：
```bash
# 参数 ['cs.CL'] 可替换为你需要的类别
python -c "from app.services.workflow_service import workflow_service; workflow_service.process_public_papers_workflow(['cs.CL'])"
```

#### 3. 仅测试“个性化筛选” (Personalized Filter)
假设数据库中已有今日抓取的论文 (`daily_papers`)，你可以单独测试 LLM 对用户的筛选逻辑：
```bash
python -c "from app.services.scheduler import scheduler_service; scheduler_service.process_personalized_papers()"
```

#### 4. 仅测试“报告生成与邮件发送” (Report & Email)
假设已经完成了个性化筛选 (`user_paper_states` 表中有数据)，你可以单独测试报告生成和邮件推送：
```bash
python -c "from app.services.scheduler import scheduler_service; scheduler_service.generate_report_job()"
```

---

### 方式二：API 接口测试 (推荐集成测试)

启动后端服务后，可以通过 HTTP 请求触发任务。这种方式适合测试前后端联动或在服务运行时触发。

**启动服务**:
```bash
python -m uvicorn app.main:app --reload
```

#### 1. 触发完整每日工作流
*   **Endpoint**: `POST /api/v1/workflow/trigger-daily`
*   **描述**: 异步触发完整的每日更新流程。
*   **测试命令**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/workflow/trigger-daily \
    -H "Authorization: Bearer <YOUR_TOKEN>"
    ```

#### 2. 仅触发报告生成 (用于测试邮件)
*   **Endpoint**: `POST /api/v1/workflow/trigger-report-only`
*   **描述**: 异步触发报告生成和邮件发送任务。
*   **测试命令**:
    ```bash
    curl -X POST http://localhost:8000/api/v1/workflow/trigger-report-only \
    -H "Authorization: Bearer <YOUR_TOKEN>"
    ```

---

## 🔍 常见问题排查

1.  **爬虫失败/无数据**:
    *   检查 `daily_papers` 表是否为空。
    *   检查网络是否能访问 Arxiv。
    *   查看终端输出的 Scrapy 日志。

2.  **LLM 筛选全被拒绝**:
    *   检查 `profiles` 表中用户的 `focus` (关注点) 是否设置正确。
    *   在 `app/services/paper_service.py` 中打开调试打印，查看 LLM 返回的原始 JSON。

3.  **邮件未发送**:
    *   检查用户 Profile 中的 `info.receive_email` 是否为 `true`。
    *   检查 `.env` 中的 `SMTP_SERVER`, `SENDER_EMAIL`, `SENDER_PASSWORD` 是否正确。
    *   检查 `system_logs` 表中是否有报错信息。
