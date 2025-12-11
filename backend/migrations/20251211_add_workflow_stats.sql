-- Add new columns to workflow_steps table for cost tracking and optimization
ALTER TABLE workflow_steps 
ADD COLUMN IF NOT EXISTS model_name text,
ADD COLUMN IF NOT EXISTS cache_hit_tokens integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS request_count integer DEFAULT 0;

COMMENT ON COLUMN workflow_steps.model_name IS '使用的模型名称';
COMMENT ON COLUMN workflow_steps.cache_hit_tokens IS '缓存命中的 Token 数';
COMMENT ON COLUMN workflow_steps.request_count IS '该步骤内发起的 API 请求总数';
