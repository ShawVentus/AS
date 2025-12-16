-- 创建工作流执行记录表
CREATE TABLE IF NOT EXISTS workflow_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_type TEXT NOT NULL, -- 工作流类型，如 'daily_update'
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, paused
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_steps INT DEFAULT 0,
    completed_steps INT DEFAULT 0,
    current_step TEXT,
    metadata JSONB DEFAULT '{}'::jsonb, -- 额外元数据
    total_tokens_input INT DEFAULT 0, -- 输入 Token 总消耗
    total_tokens_output INT DEFAULT 0, -- 输出 Token 总消耗
    total_cost DECIMAL(10, 6) DEFAULT 0, -- 总成本（美元）
    error TEXT, -- 错误信息
    error_stack TEXT, -- 错误堆栈
    updated_at TIMESTAMPTZ DEFAULT NOW(), -- 最后更新时间
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建工作流步骤记录表
CREATE TABLE IF NOT EXISTS workflow_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id UUID NOT NULL REFERENCES workflow_executions(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL, -- 步骤名称
    step_order INT NOT NULL, -- 步骤顺序
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed, skipped
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    duration_ms INT DEFAULT 0, -- 耗时（毫秒）
    error_message TEXT,
    error_stack TEXT,
    metrics JSONB DEFAULT '{}'::jsonb, -- 性能指标
    tokens_input INT DEFAULT 0, -- 输入 Token 消耗
    tokens_output INT DEFAULT 0, -- 输出 Token 消耗
    cost DECIMAL(10, 6) DEFAULT 0, -- 步骤成本（美元）
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 创建索引以优化查询
CREATE INDEX IF NOT EXISTS idx_workflow_executions_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_workflow_executions_created_at ON workflow_executions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_workflow_steps_execution_id ON workflow_steps(execution_id);
