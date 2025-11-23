# ArxivScout Backend

这是 ArxivScout 的后端服务，基于 FastAPI 构建。目前提供 Mock 数据以支持前端开发。

## 环境准备

确保您已经激活了 `arxivscout` conda 环境：

```bash
conda activate arxivscout
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 启动服务

您有两种方式启动服务，取决于您当前的目录位置。

### 启动方式

由于代码已调整为支持在 `backend` 目录下运行，请使用以下命令启动：

```bash
# 1. 进入 backend 目录
cd backend

# 2. 启动服务
# 注意：模块路径是 main:app (不再是 backend.main:app)
python -m uvicorn main:app --reload --port 8000
```

> **提示**: 如果您在项目根目录 (`AS/`) 下，也可以使用 `python -m uvicorn backend.main:app ...`，但需要确保 Python 路径配置正确。推荐进入 `backend` 目录启动。

## API 文档

启动成功后，访问以下地址查看接口文档：

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

## 目录结构

- `models/`: Pydantic 数据模型
- `services/`: 业务逻辑 (目前为 Mock 实现)
- `api/endpoints/`: API 路由
- `main.py`: 应用入口
