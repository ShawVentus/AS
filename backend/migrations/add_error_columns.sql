-- 为 workflow_executions 表添加错误信息字段
ALTER TABLE workflow_executions 
ADD COLUMN IF NOT EXISTS error TEXT,
ADD COLUMN IF NOT EXISTS error_stack TEXT,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 创建更新时间触发器（可选，确保 updated_at 自动更新）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_workflow_executions_updated_at 
    BEFORE UPDATE ON workflow_executions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();
