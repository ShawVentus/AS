# RLS 启用后表写入测试

## 测试目的

验证为 `email_analytics`、`system_logs`、`report_feedback` 三个表启用 RLS（Row Level Security）后，使用 Service Role Key 是否能正常写入数据。

## 测试场景

1. **email_analytics** - 邮件分析事件记录
2. **system_logs** - 系统错误日志记录
3. **report_feedback** - 用户报告反馈记录

## 使用方法

### 1. 确保已配置 Service Key

检查 `backend/.env` 文件中是否配置了：

```bash
SUPABASE_SERVICE_KEY=sb_secret_xxx
```

### 2. 在 Supabase 启用 RLS

为三个表启用 RLS（如已完成可跳过）：

```sql
ALTER TABLE email_analytics ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_feedback ENABLE ROW LEVEL SECURITY;
```

### 3. 运行测试脚本

```bash
cd backend/tests/12.18_1644_RLS表写入测试
conda activate arxivscout  # 激活虚拟环境
python test_rls_tables.py
```

### 4. 查看测试结果

测试结果会实时输出到控制台，并保存到 `result/test_result.txt` 文件。

## 预期结果

✅ **所有测试通过**：说明 Service Key 成功绕过 RLS，可以正常写入数据

❌ **部分测试失败**：可能原因：

- Service Key 未正确配置
- 数据库连接使用了 Anon Key 而非 Service Key
- RLS Policy 设置有问题

## 测试数据清理

脚本运行结束后会询问是否清理测试数据：

- 输入 `y`：自动删除插入的测试记录
- 输入 `n`：保留数据，可在 Supabase 控制台手动查看

## 文件结构

```
12.18_1644_RLS表写入测试/
├── test_rls_tables.py  # 测试脚本
├── README.md           # 本说明文档
└── result/             # 测试结果输出目录
    └── test_result.txt # 测试结果日志
```
